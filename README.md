# The Bot of Many Things
## Rolling Dice
### Roll dice:
```
![roll_command] [description]
```
Examples:
- `!d20+6 Longsword TO HIT`
- `!d10+d6+4 Eldritch Bolt + Hex DMG`


### Roll dice against target value: 
```
![roll_command]=[target] [description]
``` 
Examples:
- `!d20+4=15 Eldritch Bolt against AC15`
- `!d10=10 Death Save`

### Roll and keep only a specific number of dice: 
```
![roll_command]k[num] [description]
``` 
Examples:
- `!4d6k3 Stat Roll`


## Aliases
You can create aliases for regularily used roll commands:

### Create an alias 
```
!a [alias_name] [roll_command] [description]
```
Examples:
- `!a init d20+2 Initiative`
- `!a death d10=10 Death Save`


### Use an alias
```
![alias_name]
```
Examples:
- `!init`
- `!death`

### Delete an alias 
```
!a [alias_name] (without a command)
``` 
Examples:
- `!a init`
- `!a death`

### List your current aliases 
```
!list or !l
```

Aliases are saved on a per user basis.

## Initiative Tracker
You can add a player/monster to the initiative tracker.

### Add to the initiative tracker
```
!inita [value/roll_command] [name]
!initadd [value/roll_command] [name]
``` 
Examples:
- `!inita 18 Player1`
- `!inita d20+2 Monsters`
- `!inita`

If you just type `!inita` - without a value and name, the bot will look through your aliases for one with the name `init or initiative` and use it to add you to the tracker. 

### Clear/Delete from the initiative tracker
```
!initd [name]  
!initdel [name]  
!initd   
``` 
If no name is given - the tracker will be cleared.

Examples:
- `!initd`
- `!initd Monsters`

### Move the initiative tracker to the bottom of the channel
```
!inits or !initshow
```

## Item Prices
### Search the item price list
```
!item [item_name]  
!i [item_name]  
``` 
Examples:
- `!i axe`
- `!i armor`

### Add to the item price list
```
!itemadd [item_name] [item_prices] 
!ia [item_name] [item_prices]
``` 
Examples:
- `!ia "Night Vision Goggles" "100 gp | 75 gp | 150 gp"`

### delete from the item price list
```
!itemdel [item_name] 
!id [item_name]
``` 
Examples:
- `!id Night Vision Goggles`
