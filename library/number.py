from typing import Any, SupportsInt, Union

Base = Union[int, str]


def digit_to_char(digit: int) -> str:
    if digit < 10:
        return str(digit)
    return chr(ord('A') + digit - 10)


def char_to_digit(char: str) -> int:
    if '0' <= char <= '9':
        return ord(char) - ord('0')
    if 'A' <= char.upper() <= 'Z':
        return ord(char.upper()) - ord('A') + 10
    raise ValueError(f'Invalid char: {char}')


def positiveBaseStr(number: int, base: int) -> str:
    if number < 0:
        return f'-{positiveBaseStr(-number, base)}'
    d: int
    m: int
    d, m = divmod(number, base)
    if d > 0:
        return positiveBaseStr(d, base) + digit_to_char(m)
    return digit_to_char(m)


def negativeBaseStr(i: int, base: int) -> str:
    digits: str = ''
    if not i:
        digits = '0'
    else:
        while i != 0:
            remainder: int
            i, remainder = divmod(i, base)
            if remainder < 0:
                i, remainder = i + 1, remainder - base
            digits = digit_to_char(remainder) + digits
    return digits


def negativeBaseInt(s: str, base: int) -> int:
    num: int = 0
    power: int = 1
    digit: str
    for digit in s[::-1]:
        bit: int = char_to_digit(digit)
        if bit >= abs(base):
            raise ValueError(f'''invalid literal for negativeBaseInt() with \
base {base}: {digit}''')
        num += bit * power
        power *= base
    return num


def factorialBaseStr(i: int) -> str:
    if i < 0:
        raise ValueError('factorial base does not have negative numbers')
    digits: str = ''
    base: int = 1
    if not i:
        digits = '0'
    else:
        while i != 0:
            remainder: int
            i, remainder = divmod(i, base)
            digits = digit_to_char(remainder) + digits
            base += 1
            if base >= 36:
                raise ValueError(
                    'Value too large to represent in factorial base')
    return digits


def factorialBaseInt(s: str) -> int:
    if len(s) >= 36:
        raise ValueError('not enough digits to represent')
    num: int = 0
    power: int = 1
    digit: str
    i: int
    for i, digit in enumerate(reversed(s)):
        bit: int = char_to_digit(digit)
        if bit > i:
            raise ValueError(f'invalid literal for factorialBaseInt(): {bit}')
        num += bit * power
        power *= i + 1
    return num


def balancedBaseStr(i: int) -> str:
    digits: str = ''
    if not i:
        digits = '0'
    else:
        while i != 0:
            remainder: int = i % 3
            if remainder == 0 or remainder == 1:
                digits = str(remainder) + digits
            else:
                digits = 'T' + digits
                i += 1
            i //= 3
    return digits


def balancedBaseInt(s: str) -> int:
    num: int = 0
    power: int = 1
    digit: str
    for digit in s[::-1]:
        bit: int
        if digit == '0':
            bit = 0
        elif digit == '1':
            bit = 1
        elif digit == 'T' or digit == 't':
            bit = -1
        else:
            raise ValueError('invalid literal for balancedBaseInt()')
        num += bit * power
        power *= 3
    return num


class Number:
    def __init__(self,
                 value: Union[int, str]=0,
                 base: Union[int, str]=10) -> None:
        self._value: int
        self._base: Base
        if isinstance(value, int):
            valid: bool = False
            if isinstance(base, int):
                if -36 <= base <= 36 and not (-2 < base < 2):
                    valid = True
            if isinstance(base, str):
                base = base.lower()
                if base == '!' and value >= 0:
                    valid = True
                if base == 't':
                    valid = True
            if valid:
                self._value = value
                self._base = base
                return
        if isinstance(value, str):
            if isinstance(base, int):
                self._base = base
                if base < 0:
                    self._value = self.int_negative_base(value, base)
                    return
                if base > 0:
                    self._value = self.int_positive_base(value, base)
                    return
            if isinstance(base, str):
                self._base = base.lower()
                if self._base == '!':
                    self._value = self.int_factorial_base(value)
                    return
                if self._base == 't':
                    self._value = self.int_balanced_base(value)
                    return
        raise ValueError('Invalid value or base')

    @staticmethod
    def int_positive_base(value: str, base: int) -> int:
        if not value:
            raise ValueError('value is invalid')
        if base > 36 or base < 2:
            raise ValueError(f'Invalid base: {base}')
        return int(value, base)

    @staticmethod
    def int_negative_base(value: str, base: int) -> int:
        if not value:
            raise ValueError('value is invalid')
        if base < -36 or base > -2:
            raise ValueError(f'Invalid base: {base}')
        num: int = 0
        power: int = 1
        digit: str
        for digit in value[::-1]:
            bit: int = char_to_digit(digit)
            if bit >= abs(base):
                raise ValueError(f'''invalid literal for negative base \
{base}: {digit}''')
            num += bit * power
            power *= base
        return num

    @staticmethod
    def int_factorial_base(value: str) -> int:
        if not value:
            raise ValueError('value is invalid')
        if len(value) >= 36:
            raise ValueError(f'''\
not enough digits to represent values of this size: {value}''')
        num: int = 0
        power: int = 1
        digit: str
        i: int
        for i, digit in enumerate(reversed(value)):
            bit: int = char_to_digit(digit)
            if bit > i:
                raise ValueError(
                    f'invalid literal for factorialBaseInt(): {bit}')
            num += bit * power
            power *= i + 1
        return num

    @staticmethod
    def int_balanced_base(value: str) -> int:
        if not value:
            raise ValueError('value is invalid')
        num: int = 0
        power: int = 1
        digit: str
        for digit in value[::-1]:
            bit: int
            if digit == '0':
                bit = 0
            elif digit == '1':
                bit = 1
            elif digit == 'T' or digit == 't':
                bit = -1
            else:
                raise ValueError('invalid literal for balanced ternary base')
            num += bit * power
            power *= 3
        return num

    @property
    def base(self) -> Base:
        return self._base

    def __str__(self) -> str:
        if not hasattr(self, '_str'):
            if isinstance(self._base, int):
                if self._base < 0:
                    self._str = self.str_negative_base(self._value, self._base)
                else:
                    self._str = self.str_positive_base(self._value, self._base)
            if self._base == '!':
                self._str = self.str_factorial_base(self._value)
            if self._base == 't':
                self._str = self.str_balanced_base(self._value)
            if not hasattr(self, '_str'):
                self._str = super().__str__()

        return self._str

    @staticmethod
    def str_positive_base(value: int, base: int) -> str:
        if base > 36 or base < 2:
            raise ValueError(f'Invalid base: {base}')
        digits: str = ''
        sign: str = ''
        if value < 0:
            sign = '-'
            value = -value
        if not value:
            digits = '0'
        else:
            value_: int = value
            while value_ != 0:
                remainder: int
                value_, remainder = divmod(value_, base)
                digits = digit_to_char(remainder) + digits
        return sign + digits

    @staticmethod
    def str_negative_base(value: int, base: int) -> str:
        if base < -36 or base > -2:
            raise ValueError(f'Invalid base: {base}')
        digits: str = ''
        if not value:
            digits = '0'
        else:
            value_: int = value
            while value_ != 0:
                remainder: int
                value_, remainder = divmod(value_, base)
                if remainder < 0:
                    value_, remainder = value_ + 1, remainder - base
                digits = digit_to_char(remainder) + digits
        return digits

    @staticmethod
    def str_factorial_base(value: int) -> str:
        if value < 0:
            raise ValueError('factorial base does not have negative numbers')
        digits: str = ''
        base: int = 1
        if not value:
            digits = '0'
        else:
            value_: int = value
            while value_ != 0:
                remainder: int
                value_, remainder = divmod(value_, base)
                digits = digit_to_char(remainder) + digits
                base += 1
                if base >= 36:
                    raise ValueError(
                        'Value too large to represent in factorial base')
        return digits

    @staticmethod
    def str_balanced_base(value: int) -> str:
        digits: str = ''
        if not value:
            digits = '0'
        else:
            value_: int = value
            while value_ != 0:
                remainder: int = value_ % 3
                if remainder == 0 or remainder == 1:
                    digits = str(remainder) + digits
                else:
                    digits = 'T' + digits
                    value_ += 1
                value_ //= 3
        return digits

    def __int__(self) -> int:
        return self._value

    def as_base(self, base: Base) -> 'Number':
        return Number(self._value, base)

    def with_value(self, value: int) -> 'Number':
        return Number(value, self._base)

    def __add__(self, other: SupportsInt) -> 'Number':
        return Number(self._value + int(other), self._base)

    def __sub__(self, other: SupportsInt) -> 'Number':
        return Number(self._value - int(other), self._base)

    def __mul__(self, other: SupportsInt) -> 'Number':
        return Number(self._value * int(other), self._base)

    def __abs__(self) -> 'Number':
        if self._value < 0:
            return Number(-self._value, self._base)
        else:
            return self

    def __eq__(self, other: Any) -> bool:
        return self._value == other
