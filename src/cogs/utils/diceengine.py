from random import randint, seed

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
        if any(x not in 'd+-0123456789' for x in arg):
            raise ValueError('invalid dice-roll string ' + arg)
        static = 0
        rolls = []
        for group in self.split(arg):
            mul = int(group[0] + '1')
            group = group[1:]
            if not 'd' in group:
                static += int(group) * mul
                continue
            num_dice, dice_type = group.split('d')
            num_dice = 1 if not num_dice else int(num_dice)
            dice_type = int(dice_type)
            [rolls.append(randint(1, dice_type) * mul)
             for _ in range(num_dice)]
        return (static + sum(rolls), rolls, static)
