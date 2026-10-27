from test.bases import WorldTestBase

DLC_START_INVENTORY = {
    'Super Shotgun': 1, 'Ballista': 1, 'Chaingun': 1, 'Plasma Rifle': 1,
    'Microwave Beam': 1, 'Energy Shield': 1, 'Meat Hook': 1, 'Ice Bomb': 1,
    'Air Control': 1, 'Saving Throw': 1, 'Faster Weapon Swap': 1,
    'Progressive Health Upgrade': 2, 'Progressive Armor Upgrade': 2, 'Progressive Ammo Upgrade': 2,
}


class DoomEternalTestBase(WorldTestBase):
    game = "DOOM Eternal"
