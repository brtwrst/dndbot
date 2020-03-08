from random import randint, seed
from dataclasses import dataclass

@dataclass
class DiceResult:
    total: int
    rolls: list
    ignored: list
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
        if any(x not in 'dk+-=0123456789' for x in arg):
            raise ValueError('invalid character in dice-roll string')
        static = 0
        rolls = []
        ignored = []
        crithit = False
        critmiss = False
        success = None

        target_mode = '=' in arg
        keep_mode = 'k' in arg
        if target_mode and keep_mode:
            raise ValueError('target mode and keep mode cannot be used at the same time')

        if target_mode:
            arg, target = arg.split('=')
        else:
            target = None
        if keep_mode:
            arg, keep = arg.split('k')
        else:
            keep = None

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

        if keep:
            keep = int(keep)
            if keep < 1:
                raise ValueError('must keep at least 1 die')
            if '-' in arg:
                raise ValueError('negative rolls not allowed with keep syntax')
            while keep < len(rolls):
                ignored.append(rolls.pop(rolls.index(min(rolls))))

        total = static + sum(rolls)

        if target:
            if crithit:
                success = True
            elif critmiss:
                success = False
            else:
                success = total >= int(target)
        result = DiceResult(total, rolls, ignored, static, success, crithit, critmiss)
        return result
