#!/usr/bin/env python3
"""
ИГРА "УГАДАЙ ЧИСЛО" v2.0
Полная реализация с подсказками, статистикой, сохранением состояния и уровнями сложности.
"""

import random
import json
import os
import sys
import time
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Union

# ==================== КОНСТАНТЫ ====================
SAVE_FILE = "game_save.json"
STATS_FILE = "game_stats.json"

# ==================== КЛАСС КОНФИГУРАЦИИ ====================

class GameConfig:
    """Управление настройками игры: диапазон, сложность, попытки"""
    
    DIFFICULTY_LEVELS = {
        "легко": {"min": 1, "max": 50, "attempts": 15, "hint_after": 8},
        "средне": {"min": 1, "max": 100, "attempts": 10, "hint_after": 6},
        "сложно": {"min": 1, "max": 200, "attempts": 7, "hint_after": 4},
        "эксперт": {"min": 1, "max": 500, "attempts": 5, "hint_after": 3}
    }
    
    def __init__(self, difficulty: str = "средне"):
        level = self.DIFFICULTY_LEVELS.get(difficulty, self.DIFFICULTY_LEVELS["средне"])
        self.min_num = level["min"]
        self.max_num = level["max"]
        self.max_attempts = level["attempts"]
        self.hint_after = level["hint_after"]
        self.difficulty = difficulty
        self.custom_range = None
    
    @classmethod
    def custom(cls, min_num: int, max_num: int, max_attempts: int):
        """Создание конфигурации с пользовательским диапазоном"""
        instance = cls("пользовательский")
        instance.min_num = min_num
        instance.max_num = max_num
        instance.max_attempts = max_attempts
        instance.hint_after = max_attempts // 2
        instance.custom_range = (min_num, max_num)
        return instance
    
    def to_dict(self) -> dict:
        return {
            "min_num": self.min_num,
            "max_num": self.max_num,
            "max_attempts": self.max_attempts,
            "hint_after": self.hint_after,
            "difficulty": self.difficulty
        }

# ==================== КЛАСС СТАТИСТИКИ ====================

class Statistics:
    """Хранение и управление статистикой игр"""
    
    def __init__(self):
        self.filename = STATS_FILE
        self.stats = self._load()
    
    def _load(self) -> dict:
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._default_stats()
        return self._default_stats()
    
    def _default_stats(self) -> dict:
        return {
            "total_games": 0,
            "wins": 0,
            "losses": 0,
            "total_attempts_used": 0,
            "best_game_attempts": None,
            "games_history": []
        }
    
    def save(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
    
    def add_result(self, won: bool, attempts_used: int, config: GameConfig):
        self.stats["total_games"] += 1
        if won:
            self.stats["wins"] += 1
            if (self.stats["best_game_attempts"] is None or 
                attempts_used < self.stats["best_game_attempts"]):
                self.stats["best_game_attempts"] = attempts_used
        else:
            self.stats["losses"] += 1
        
        self.stats["total_attempts_used"] += attempts_used
        self.stats["games_history"].append({
            "date": datetime.now().isoformat(),
            "won": won,
            "attempts": attempts_used,
            "difficulty": config.difficulty,
            "range": f"{config.min_num}-{config.max_num}"
        })
        
        # Ограничиваем историю 20 играми
        if len(self.stats["games_history"]) > 20:
            self.stats["games_history"] = self.stats["games_history"][-20:]
        self.save()
    
    def display(self):
        print("\n" + "=" * 50)
        print("            📊 СТАТИСТИКА ИГР")
        print("=" * 50)
        print(f"Всего игр:           {self.stats['total_games']}")
        
        if self.stats['total_games'] > 0:
            winrate = (self.stats['wins'] / self.stats['total_games']) * 100
            print(f"Побед:              {self.stats['wins']}")
            print(f"Поражений:          {self.stats['losses']}")
            print(f"Процент побед:      {winrate:.1f}%")
            print(f"Среднее попыток:    {self.stats['total_attempts_used'] / self.stats['total_games']:.1f}")
            
            if self.stats['best_game_attempts']:
                print(f"Лучший результат:   {self.stats['best_game_attempts']} попыток")
            
            print("\n📜 ИСТОРИЯ ПОСЛЕДНИХ ИГР:")
            for game in self.stats['games_history'][-5:]:
                result = "✅ ПОБЕДА" if game["won"] else "❌ ПОРАЖЕНИЕ"
                print(f"  {game['date'][:10]} | {result} | {game['attempts']} попыток | {game['difficulty']}")

# ==================== ОСНОВНОЙ КЛАСС ИГРЫ ====================

class GuessNumberGame:
    """Основной класс игры "Угадай число"."""
    
    def __init__(self):
        self.config: Optional[GameConfig] = None
        self.secret_number: Optional[int] = None
        self.attempts_made: int = 0
        self.previous_guesses: List[int] = []
        self.hint_used: bool = False
        self.start_time: Optional[float] = None
        self.stats = Statistics()
        self.commands = {"hint", "save", "stats", "quit", "new"}
    
    # -------------------- ИНСТРУКЦИИ --------------------
    
    def show_instructions(self):
        """Вывод инструкций по игре при запуске."""
        print("\n" + "=" * 60)
        print("                 🎮 ИГРА «УГАДАЙ ЧИСЛО» 🎮")
        print("=" * 60)
        print("\n📖 ПРАВИЛА ИГРЫ:")
        print("  1. Компьютер загадывает случайное число в заданном диапазоне")
        print("  2. Вы вводите свои варианты чисел")
        print("  3. После каждой попытки вы получаете подсказку: больше или меньше")
        print("  4. Игра заканчивается, когда вы угадаете число или кончатся попытки")
        print("\n💡 ДОСТУПНЫЕ КОМАНДЫ:")
        print("  • число      — сделать попытку")
        print("  • hint       — получить подсказку (доступно после определённого числа попыток)")
        print("  • save       — сохранить текущую игру")
        print("  • stats      — показать статистику всех игр")
        print("  • quit       — выйти из игры")
        print("  • new        — начать новую игру")
        print("\n" + "=" * 60)
    
    # -------------------- НАСТРОЙКА ИГРЫ --------------------
    
    def setup_game(self):
        """Настройка параметров игры перед началом."""
        print("\n🎯 ВЫБОР СЛОЖНОСТИ:")
        print("  1. Легко   (1-50, 15 попыток, подсказка с 8-й)")
        print("  2. Средне  (1-100, 10 попыток, подсказка с 6-й)")
        print("  3. Сложно  (1-200, 7 попыток, подсказка с 4-й)")
        print("  4. Эксперт (1-500, 5 попыток, подсказка с 3-й)")
        print("  5. Свой диапазон")
        
        while True:
            choice = input("\nВыберите уровень (1-5): ").strip()
            if choice == "1":
                self.config = GameConfig("легко")
                break
            elif choice == "2":
                self.config = GameConfig("средне")
                break
            elif choice == "3":
                self.config = GameConfig("сложно")
                break
            elif choice == "4":
                self.config = GameConfig("эксперт")
                break
            elif choice == "5":
                self.config = self._custom_setup()
                break
            else:
                print("❌ Неверный выбор. Введите число от 1 до 5.")
    
    def _custom_setup(self) -> GameConfig:
        """Настройка пользовательского диапазона."""
        while True:
            try:
                min_val = int(input("Введите минимальное число: "))
                max_val = int(input("Введите максимальное число: "))
                if min_val >= max_val:
                    print("❌ Минимум должен быть меньше максимума.")
                    continue
                attempts = int(input("Введите количество попыток: "))
                if attempts <= 0:
                    print("❌ Количество попыток должно быть положительным.")
                    continue
                return GameConfig.custom(min_val, max_val, attempts)
            except ValueError:
                print("❌ Введите корректные числа.")
    
    # -------------------- ИГРОВАЯ ЛОГИКА --------------------
    
    def new_game(self):
        """Начало новой игры."""
        self.setup_game()
        self.secret_number = random.randint(self.config.min_num, self.config.max_num)
        self.attempts_made = 0
        self.previous_guesses = []
        self.hint_used = False
        self.start_time = time.time()
        
        print(f"\n🎲 ИГРА НАЧАЛАСЬ!")
        print(f"📊 Диапазон: от {self.config.min_num} до {self.config.max_num}")
        print(f"🎯 Количество попыток: {self.config.max_attempts}")
        print(f"💡 Подсказка станет доступна после {self.config.hint_after} попыток")
        print("=" * 50)
    
    def get_current_range(self) -> Tuple[int, int]:
        """Определение текущего возможного диапазона на основе предыдущих попыток."""
        low = self.config.min_num
        high = self.config.max_num
        
        for guess in self.previous_guesses:
            if guess < self.secret_number and guess > low:
                low = guess
            elif guess > self.secret_number and guess < high:
                high = guess
        
        return low + 1, high - 1
    
    def show_hint(self):
        """Предоставление подсказки о диапазоне."""
        if self.attempts_made >= self.config.hint_after and not self.hint_used:
            low, high = self.get_current_range()
            print(f"💡 ПОДСКАЗКА: Загаданное число находится между {low} и {high}")
            self.hint_used = True
        elif self.hint_used:
            print("💡 Вы уже использовали подсказку в этой игре.")
        else:
            remaining = self.config.hint_after - self.attempts_made
            print(f"💡 Подсказка станет доступна через {remaining} попыток.")
    
    def save_game(self):
        """Сохранение текущего состояния игры."""
        save_data = {
            "secret_number": self.secret_number,
            "config": self.config.to_dict(),
            "attempts_made": self.attempts_made,
            "previous_guesses": self.previous_guesses,
            "hint_used": self.hint_used,
            "start_time": self.start_time
        }
        try:
            with open(SAVE_FILE, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            print("💾 Игра сохранена! В следующий запуск введите 'load' для загрузки.")
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
    
    def load_game(self) -> bool:
        """Загрузка сохранённой игры."""
        if not os.path.exists(SAVE_FILE):
            print("❌ Нет сохранённой игры.")
            return False
        
        try:
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.secret_number = data["secret_number"]
            self.attempts_made = data["attempts_made"]
            self.previous_guesses = data["previous_guesses"]
            self.hint_used = data["hint_used"]
            self.start_time = data["start_time"]
            
            # Восстановление конфигурации
            cfg = data["config"]
            self.config = GameConfig.custom(
                cfg["min_num"], cfg["max_num"], cfg["max_attempts"]
            ) if cfg["difficulty"] == "пользовательский" else GameConfig(cfg["difficulty"])
            
            print(f"✅ Игра загружена! Вы уже сделали {self.attempts_made} попыток.")
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            return False
    
    def get_valid_input(self) -> Union[int, str]:
        """Получение корректного ввода от пользователя с валидацией."""
        while True:
            user_input = input(f"\n🎯 ПОПЫТКА {self.attempts_made + 1}/{self.config.max_attempts}\n🔢 Введите число: ").strip().lower()
            
            if not user_input:
                print("❌ Ввод не может быть пустым!")
                continue
            
            # Проверка команд
            if user_input in self.commands:
                return user_input
            
            # Проверка на число и диапазон
            try:
                guess = int(user_input)
                if self.config.min_num <= guess <= self.config.max_num:
                    return guess
                else:
                    print(f"❌ Число должно быть в диапазоне от {self.config.min_num} до {self.config.max_num}!")
            except ValueError:
                print("❌ Ошибка: Введите целое число или доступную команду (hint, save, stats, quit, new)!")
    
    def make_guess(self, guess: int) -> bool:
        """Обработка попытки угадывания. Возвращает True, если игра окончена."""
        self.previous_guesses.append(guess)
        self.attempts_made += 1
        
        print(f"\n📝 Ваши предыдущие попытки: {self.previous_guesses}")
        
        if guess == self.secret_number:
            time_spent = time.time() - self.start_time
            print(f"\n🎉 ПОЗДРАВЛЯЮ! Вы угадали число {self.secret_number}!")
            print(f"📊 Количество попыток: {self.attempts_made}")
            print(f"⏱️ Время игры: {time_spent:.1f} секунд")
            
            # Сохраняем статистику
            self.stats.add_result(True, self.attempts_made, self.config)
            return True
        
        elif guess < self.secret_number:
            print(f"📈 Слишком маленькое! Загаданное число БОЛЬШЕ.")
        else:
            print(f"📉 Слишком большое! Загаданное число МЕНЬШЕ.")
        
        # Показываем количество оставшихся попыток
        remaining = self.config.max_attempts - self.attempts_made
        print(f"💪 Осталось попыток: {remaining}")
        
        # Проверка окончания игры
        if remaining == 0:
            print(f"\n❌ ИГРА ОКОНЧЕНА! У вас закончились попытки.")
            print(f"🔢 Загаданное число было: {self.secret_number}")
            self.stats.add_result(False, self.attempts_made, self.config)
            return True
        
        return False
    
    # -------------------- ОСНОВНОЙ ЦИКЛ --------------------
    
    def play(self):
        """Основной игровой цикл."""
        self.show_instructions()
        
        # Проверка наличия сохранённой игры
        if os.path.exists(SAVE_FILE):
            choice = input("Обнаружена сохранённая игра. Загрузить? (да/нет): ").strip().lower()
            if choice in ('да', 'yes', 'y', 'load'):
                if self.load_game():
                    pass  # Игра загружена, продолжаем
                else:
                    self.new_game()
            else:
                self.new_game()
        else:
            self.new_game()
        
        game_over = False
        
        while not game_over:
            user_input = self.get_valid_input()
            
            # Обработка команд
            if user_input == "quit":
                print("👋 Спасибо за игру! До свидания!")
                sys.exit(0)
            elif user_input == "new":
                self.new_game()
                game_over = False
                continue
            elif user_input == "stats":
                self.stats.display()
                continue
            elif user_input == "save":
                self.save_game()
                continue
            elif user_input == "hint":
                self.show_hint()
                continue
            else:
                # Это число
                game_over = self.make_guess(user_input)
        
        # Игра окончена, спрашиваем о повторной игре
        self.play_again()
    
    def play_again(self):
        """Запрос на повторную игру."""
        while True:
            choice = input("\n🎮 Сыграем ещё? (да/нет): ").strip().lower()
            if choice in ('да', 'yes', 'y', 'д'):
                self.new_game()
                self.play()
                break
            elif choice in ('нет', 'no', 'n'):
                print("👋 Спасибо за игру! До свидания!")
                sys.exit(0)
            else:
                print("❌ Введите 'да' или 'нет'.")

# ==================== ТОЧКА ВХОДА ====================

def main():
    """Главная функция программы."""
    try:
        game = GuessNumberGame()
        game.play()
    except KeyboardInterrupt:
        print("\n\n👋 Программа прервана пользователем. До свидания!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Непредвиденная ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()