from random import randint, seed
from dataclasses import dataclass

@dataclass
class DiceResult:
    total: int
    rolls: list
    static: int
    success: bool
    crithit: bool
    critmiss: bool

class DiceEngine():
    def __init__(self):
        seed()

    @staticmethod
    def split(arg: str):
        splits = []
        if arg[0] not in '+-':
            arg = '+' + arg
        current = []
        for c in arg:
            if c in '+-' and current:
                splits.append(''.join(current))
                current = [c]
            else:
                current.append(c)
        res = splits + [''.join(current)]
        return res

    def __call__(self, arg):
        if not arg:
            return
        arg = arg.lower()
        if any(x not in 'd+-=0123456789' for x in arg):
            raise ValueError('invalid dice-roll string ' + arg)
        static = 0
        rolls = []
        crithit = False
        critmiss = False
        success = None
        if '=' in arg:
            arg, target = arg.split('=')
        else:
            target = None
        for group in self.split(arg):
            mul = int(group[0] + '1')
            group = group[1:]
            if not 'd' in group:
                static += int(group) * mul
                continue
            num_dice, dice_type = group.split('d')
            num_dice = 1 if not num_dice else int(num_dice)
            dice_type = int(dice_type)
            new_rolls = [(randint(1, dice_type) * mul) for _ in range(num_dice)]
            if dice_type == 20 and num_dice == 1:
                if 1 in new_rolls:
                    critmiss = True
                elif 20 in new_rolls:
                    crithit = True
            rolls += new_rolls
        total = static + sum(rolls)
        if target:
            if crithit:
                success = True
            elif critmiss:
                success = False
            else:
                success = total >= int(target)
        result = DiceResult(total, rolls, static, success, crithit, critmiss)
        return result
