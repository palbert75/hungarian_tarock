"""Paired A/B test for bot tactics.

The same deals are played twice: once with every bot on the adopted tactics,
once with two seats using the extra tactic(s) as well. Prints the mean change
in those two seats' score per hand, its standard error and z value.

    cd server; PYTHONPATH=. python tools/ab_tactics.py 3000 some_tactic other,combined
"""
import asyncio, logging, sys, math
import structlog
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL))
import bots.strategy as S
from bots.view import build_view
from models.game_state import GamePhase
from tests.service_helpers import make_service, seed

async def hand(n, tactics):
    seed(n)
    variant_seats = {0,2} if n%2==0 else {1,3}
    def decide(g,p):
        S.TACTICS = (set(S.ADOPTED) | set(tactics)) if p in variant_seats else set(S.ADOPTED)
        return S.decide(build_view(g,p))
    service, manager, rec = make_service(decide=decide)
    room = manager.create_room("s0","Anna"); room.fill_bots(); room.players[0].is_ready=True
    await service.start_game(room)
    while room.game_state.phase != GamePhase.GAME_END:
        pos = service.turn_position(room); pl = room.game_state.get_player(pos)
        await service.apply_decision(room, pl, decide(room.game_state,pos))
    r = rec.of("game_over")[-1]; r=r.get("data",r)
    pts = r["declarer_team_points"]
    return sum(v-50 for k,v in r["player_scores"].items() if int(k) in variant_seats)

async def main(N, specs):
    base=[await hand(n, []) for n in range(N)]
    specs=[x for x in specs]
    for spec in specs:
        t=spec.split(',')
        d=[]
        for n in range(N):
            d.append(await hand(n,t)-base[n])
        m=sum(d)/N; sd=math.sqrt(sum((x-m)**2 for x in d)/N); se=sd/math.sqrt(N) or 1e-9
        changed=sum(1 for x in d if x!=0)
        print(f"{spec:70s} mean {m:+.3f} se {se:.3f} z {m/se:+.1f} hands changed {changed}", flush=True)
asyncio.run(main(int(sys.argv[1]), sys.argv[2:]))
