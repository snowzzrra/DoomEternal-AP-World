from copy import deepcopy
import asyncio
from collections import defaultdict
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

from worlds import network_data_package
from worlds.AutoWorld import data_package_checksum
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.killsanity_plan import KILLSANITY_ADDRESS_BASE, build_killsanity_plan


def test_room_package_unites_thresholds_without_mutating_other_rooms():
    original = deepcopy(network_data_package["games"][DoomEternalWorld.game])
    first = SimpleNamespace(killsanity_plan=build_killsanity_plan({"enabled": True}, 13))
    second = SimpleNamespace(killsanity_plan=build_killsanity_plan({"enabled": True, "interval": 75}, 2))
    room = SimpleNamespace(worlds={1: first, 2: second}, get_game_players=lambda game: (1, 2))
    multidata = {"datapackage": {DoomEternalWorld.game: original}}
    DoomEternalWorld.stage_modify_multidata(room, multidata)
    package = multidata["datapackage"][DoomEternalWorld.game]
    assert package["location_name_to_id"]["Killed 100 Enemies"] == KILLSANITY_ADDRESS_BASE + 100
    assert package["location_name_to_id"]["Killed 75 Enemies"] == KILLSANITY_ADDRESS_BASE + 75
    assert package["checksum"] == data_package_checksum({key: value for key, value in package.items()
                                                         if key != "checksum"})
    assert "Killed 75 Enemies" in package["location_name_groups"]["Everywhere"]
    assert package["checksum"] != original["checksum"]
    assert network_data_package["games"][DoomEternalWorld.game] == original
    from apmw.multiserver.gamespackagecache import GamesPackageCache
    from MultiServer import Context, process_client_cmd
    from NetUtils import encode
    from Utils import restricted_loads
    import pickle

    restored = restricted_loads(pickle.dumps(multidata))
    server = SimpleNamespace(
        logger=logging.getLogger(__name__), played_games={DoomEternalWorld.game},
        games_package_cache=GamesPackageCache(), reduced_games_package={},
        item_name_groups={}, location_name_groups={}, checksums={},
        item_names=defaultdict(dict), location_names=defaultdict(dict),
        all_item_and_group_names={}, all_location_and_group_names={}, send_msgs=AsyncMock(),
    )
    Context._load_data_package(server, restored["datapackage"])
    Context._init_game_data(server)
    assert server.location_names[DoomEternalWorld.game][KILLSANITY_ADDRESS_BASE + 75] == "Killed 75 Enemies"
    client = object()
    asyncio.run(process_client_cmd(server, client, {"cmd": "GetDataPackage", "games": [DoomEternalWorld.game]}))
    returned = server.send_msgs.call_args.args[1][0]
    assert returned["data"]["games"][DoomEternalWorld.game]["checksum"] == package["checksum"]
    assert "Killed 75 Enemies" in encode([returned])
    fresh = SimpleNamespace(worlds={1: SimpleNamespace(killsanity_plan=build_killsanity_plan({}, None))},
                            get_game_players=lambda game: (1,))
    other = {"datapackage": {DoomEternalWorld.game: original}}
    DoomEternalWorld.stage_modify_multidata(fresh, other)
    assert other["datapackage"][DoomEternalWorld.game] is original
