// ---- tiny DSL ---------------------------------------------------------------
// q(text, opts, rightLabel, rightNode, downLabel): a check; one answer goes right, the other continues down
// seq(a, b, c, ...): chains checks downwards; the last item may be an action
// m(text, opts, [[label,node],...]): a check whose answers all go right
const q=(text,o,rl,rn,dl)=>({text,...(o||{}),right:rn?[[rl,rn]]:[],down:null,dl:dl||'no'});
const seq=(...xs)=>{for(let i=0;i<xs.length-1;i++)xs[i].down=[xs[i].dl,xs[i+1]];return xs[0]};
const m=(text,o,right)=>({text,...(o||{}),right,down:null});
const leaf=k=>(text,detail)=>({leaf:k,text,detail});
const BID=leaf('act'),PASS=leaf('pass'),SAY=leaf('act'),KON=leaf('honour'),OFF=leaf('off');
const T=leaf('tarokk'),S=leaf('suit'),H=leaf('honour'),X=leaf('any'),G=leaf('goto');
const L=n=>'strategy.py:'+(LM[n]||n);

// ---- A: bidding -------------------------------------------------------------
const A=seq(
  q('Do I hold an honour: skíz, XXI or pagát?',{src:L(110)},'no',PASS('Pass','no honour, no bid'),'yes'),
  q('Is there any bid I may still make?',{src:LS(`if bid is None:`)},'no',PASS('Pass'),'yes'),
  q('Did I give an invit myself, and somebody else now holds the highest bid?',{src:LS(`if view.highest_bidder != view.position:`),note:'Only reached as a hint for a human seat: bots never start an invit.'},'yes',PASS('Pass','they took my invit and will call my card')),
  q('Somebody else gave an invit, I hold the skíz or the XXI, and the candidate is below solo (or I hold 6+ tarokks)?',{src:LS(`if level < BID_LEVEL["solo"] or tarokk_count >= INVIT_SOLO_TAROKKS:`),tag:'invit_accept'},'yes',BID('Bid the candidate','take the auction, then call the invited card')),
  q('I hold the XIX, a great honour and 6+ tarokks, and a jump bid up to “one” is open?',{src:L(128),tag:'invit_give · off'},'yes',OFF('Jump bid to invite the XIX','switched off: lost points in testing')),
  q('Yield turn: I said three, one other said two, the rest passed, and I am allowed to pass (I hold the XX and a great honour)?',{src:L(132),tag:'yield_game'},'yes',PASS('Pass','yields the game: the other player calls my XX')),
  q('Do I hold the XXI?',{src:L(136)},'yes',seq(
    q('Would the candidate be solo?',{src:L(138)},'yes',PASS('Pass','never solo with the XXI')),
    BID('Bid the candidate','always bids with the XXI, up to “one”'))),
  q('Do I hold the skíz?',{src:L(142)},'yes',seq(
    q('4 or more tarokks beside the skíz?',{src:L(144)},'yes',PASS('Pass','a strong skíz stays out and waits for the XXI')),
    q('Would the candidate be above “two”?',{src:L(146)},'yes',PASS('Pass','limit reached')),
    BID('Bid the candidate','a weak skíz bids up to “two”')),'no: pagát only'),
  q('The candidate is “two” over a “three” from the seat right before me, that is the only bidding so far, and I have not bid yet?',{src:L(151),tag:'bid_over_three'},'yes',BID('Bid “two”','either a yielded game with a strong partner, or more talon cards')),
  q('Fewer than 8 tarokks?',{src:L(158)},'yes',PASS('Pass')),
  q('Would the candidate be above “two”?',{src:L(160)},'yes',PASS('Pass','limit reached')),
  BID('Bid the candidate','pagát with 8+ tarokks bids up to “two”'));
const A2=seq(
  q('Safety net after every decision above: is it a Pass that is not legal here? (On a yield turn a pass needs the XX and a great honour.)',{src:L(96)},'yes',BID('Bid the candidate instead','must hold')),
  X('The decision above stands'));

// ---- B: partner call --------------------------------------------------------
const B1=seq(
  q('Is the call fixed by the auction?',{src:L(205)},'yes',
    m('Why?',{src:L(207)},[['I accepted an invit',SAY('Call the invited card','XIX or XVIII')],['the game was yielded to me',SAY('Call the XX')]])),
  q('Do I hold the XX myself?',{src:L(210)},'no',SAY('Call the XX'),'yes'),
  SAY('Call the highest tarokk below it that I do not hold','XIX, then XVIII … down to XII; if I hold all of them, call the XX (myself)'));

// ---- B: announcements -------------------------------------------------------
const tarokkDecl=()=>q('I hold exactly 8 or exactly 9 tarokks and have not declared them?',{src:LS(`if declaration and (not my_side_declares or trull_called):`)},'yes',SAY('+ eight / nine tarokks','always declared: everybody else pays'),'then');
const ulti=()=>q('I hold the pagát and have 9+ tarokks, or 8 with three of them XVII or higher?',{src:LS(`if my_side_declares and view.holds("I") and ulti_hand`)},'yes',SAY('+ pagát ulti'),'then');
const B2=m('Which team am I on? (Certain once the card is called.)',{src:L(251)},[
  ['caller team: I am the declarer',seq(
    q('I hold the pagát but neither the skíz nor the XXI (and not the called card)?',{src:LS(`if pagat_only and not view.must_ulti:`),note:'Said first. It tells the partner that I hold no great honour, so the XXI can still be caught.'},'yes',SAY('+ pagát ulti','as information'),'then'),
    q('I accepted somebody\'s invit and hold the skíz or the XXI?',{src:L(238),tag:'invit_trull',note:'One great honour is enough here: the invit is taken to show the other one.'},'yes',SAY('+ trull'),'then'),
    q('I hold both the skíz and the XXI?',{src:L(255)},'yes',SAY('+ trull','if not already on the list; pagát and tarokk count do not matter'),'then'),
    q('I hold the pagát and have 9+ tarokks; or 8 with three of them XVII or higher, once my partner has announced four kings or declared 8 or 9 tarokks?',{src:LS(`if my_side_declares and view.holds("I") and ulti_hand`)},'yes',SAY('+ pagát ulti'),'then'),
    q('I hold 6+ tarokks and a great honour, and a non-declarer has announced something?',{src:L(264),tag:'signal_double · off'},'yes',OFF('+ double game','switched off: costs about a quarter point per hand'),'then'),
    q('I hold exactly 8 or exactly 9 tarokks, have not declared them, and trull has been called (by anyone, or by me in this turn or earlier)?',{src:LS(`if declaration and (not my_side_declares or trull_called):`)},'yes',SAY('+ eight / nine tarokks','everybody else pays'),'then'),
    G('Go to the final step'))],
  ['caller team: I hold the called card',seq(
    q('I gave an invit with the pagát as my only honour, and my card was called?',{src:L(234)},'yes',SAY('+ pagát ulti','obligatory'),'then'),
    q('6+ tarokks?',{src:L(243)},'yes',SAY('+ four kings'),'then'),
    q('5+ tarokks above the XIII?',{src:L(245),tag:'partner_double'},'yes',SAY('+ double game'),'then'),
    q('I hold both the skíz and the XXI?',{src:LS(`if view.holds("skiz") and view.holds("XXI"):`),note:'Trull means: our team holds both great honours.'},'yes',SAY('+ trull'),'no'),
    q('I hold one of them, and the declarer has not announced pagát ulti?',{src:LS(`elif (view.holds("skiz") or view.holds("XXI")) and not declarer_ulti:`),note:'A declarer without a great honour says pagát ulti. No ulti from them: the other great honour is theirs.'},'yes',SAY('+ trull','as information'),'then'),
    q('I hold the pagát and have 9+ tarokks; or 8 with three of them XVII or higher, once the declarer has announced four kings or declared 8 or 9 tarokks?',{src:LS(`if my_side_declares and view.holds("I") and ulti_hand`)},'yes',SAY('+ pagát ulti'),'then'),
    q('I hold exactly 8 or exactly 9 tarokks, have not declared them, and trull has been called (by anyone, or by me in this turn or earlier)?',{src:LS(`if declaration and (not my_side_declares or trull_called):`)},'yes',SAY('+ eight / nine tarokks','everybody else pays'),'then'),
    G('Go to the final step'))],
  ['enemy team',seq(
    tarokkDecl(),
    q('Nothing on my list, the caller team announced four kings, no kontra on it yet, and I hold 5+ tarokks above the XIII?',{src:LS(`if kind == "four_kings" and not my_side_declares and high >= KONTRA_KINGS_HIGH:`),tag:'kontra',note:'“Caller team” here means the declarer, or a non-declarer who announced something.'},'yes',KON('Kontra the four kings','strong hand')),
    G('Go to the final step','the enemy team announces nothing else'))]]);
const B3=seq(
  q('Strike from my list what may no longer be announced (already announced by anyone).',{src:L(273),rule:true},null,null,'then'),
  q('Am I on the caller team?',{src:LS(`if my_side_declares:`),note:'Announcements carry information, so the partner must get a turn to answer.'},'yes',seq(
    q('Four kings is on my list, and: double game is on it too, or I hold the pagát with 8+ tarokks, or I declare (or already declared) 8 or 9 tarokks?',{src:LS(`if "double_game" in kinds or counted or ulti_chance`)},'yes',PASS('Take four kings off my list for this turn','double game goes first; with a pagát ulti hand I want to hear four kings from my partner; a tarokk count already says “long hand”'),'then'),
    q('More than two things left on my list?',{src:LS(`return wanted[:ANNOUNCE_PER_TURN]`)},'yes',PASS('Keep the first two, in this order: trull, double game, tarokk count, four kings, pagát ulti','the rest waits for my next turn; trull is never held back, and a pagát ulti owed for an invit goes first'),'then'),
    G('Carry on below'))),
  q('Is my list empty?',{src:LS(`if not wanted and "kontra" in TACTICS:`)},'yes',seq(
    q('A known opponent announced four kings, no kontra on it yet, and I hold 6+ tarokks with two at XVII or higher?',{src:LS(`kind == "four_kings" and tarokk_count`),tag:'kontra'},'yes',KON('Kontra the four kings')),
    q('A known opponent announced pagát ulti, no kontra on it yet, and I hold 7+ tarokks?',{src:LS(`kind == "pagat_ultimo" and tarokk_count`),tag:'kontra'},'yes',KON('Kontra the pagát ulti')),
    PASS('Pass'))),
  SAY('Announce what is on the list'));

// ---- C: card play -----------------------------------------------------------
const C0=m('Can the XXI still be caught, as far as this seat can tell?',{note:'My grouping. The code checks these facts one by one inside the rules below.'},[
  ['yes',m('Branch I. No trull announced by anyone, skíz and XXI both still unplayed, and I do not hold both.',{},[
    ['I lead',G('Branch I · leading','next tree below')],['I follow',G('Branch I · following')]])],
  ['no',m('Branch II. Trull is announced (the announcing team holds both great honours), or I hold both skíz and XXI, or one of the two has been played.',{},[
    ['I lead',G('Branch II · leading')],['I follow',G('Branch II · following')]])]]);

function leadTree(two){
  const strong = two ? 'not the pagát; not the XXI while the skíz is in another hand' : 'not the pagát, not the XXI';
  const hunt=()=>seq(
    q('Are 3 or fewer tarokks still out (the XXI among them)?',{src:LS(`if skiz_card and len(out) <= 3:`)},'yes',H('Lead the skíz','three players follow: the XXI has to fall under it')),
    q('Do I have a suit card?',{src:LS(`if suit:`)},'yes',S('Lead the cheapest card of a suit whose king I do not hold','any suit if I hold every king; the XXI\'s holder may have to follow')),
    q('Do I have a tarokk other than skíz and pagát?',{src:LS(`if small:`)},'yes',T('Lead my lowest tarokk')),
    G('Carry on with the checks below','ends up leading the skíz'));
  const head=[
    q('I announced pagát ulti and still hold the pagát?',{src:LS(`if _announced(view, "pagat_ultimo", by_me=True) and view.holds("I"):`)},'yes',seq(
      q('Tarokks are still out, and I have one to lead ('+strong+')?',{src:LS(`if out and strong_tarokks():`),tag:'ulti_small'},'yes',T('Lead my lowest such tarokk','draw the tarokks, keep the pagát for the end')),
      q('Do I have a suit card?',{src:LA(`if out and strong_tarokks():`,`if low_suit:`)},'yes',S('Lead a king if I hold one, otherwise the low suit card','a king should keep the lead; keep the pagát')),
      G('Carry on with the checks below'))),
    q('Somebody not known as my teammate announced pagát ulti, I have exactly one tarokk beside the pagát, and a suit card?',{src:LS(`if ulti_against and len(plain_tarokks) == 1 and low_suit:`)},'yes',S('Lead the low suit card','keep the tarokk for the last trick'))];
  const mid = two ? [
    q('Exception: the other team announced trull, yet I hold the skíz myself and the XXI is still unplayed?',{src:L(469),tag:'skiz_hunt',note:'Their trull cannot be true, so the bot keeps waiting for the XXI.'},'yes',hunt()),
    q('Trull was called, I am on the enemy team, and I have a suit card?',{src:LS(`if _announced(view, "trull") and view.declarer_position is not None and not view.on_declarer_side and low_suit:`)},'yes',S('Lead the low suit card','general rule: once trull is called, the enemy team leads suits; with four kings or double game also announced, a suit whose king I do not hold')),
    q('General rule once trull is called: the caller team leads a tarokk. The checks below pick which one. A suit is led only with no tarokk to lead, or in the pagát ulti cases.',{rule:true},null,null,'then'),
    q('Skíz and XXI are both still unplayed, I hold neither, a known teammate who plays last to this trick seems to wait with the skíz, and I have a tarokk beside the pagát?',{src:L(479),tag:'skiz_drive'},'yes',T('Lead my highest tarokk','drive the XXI out')),
    q('Trull is announced on my side, the pagát has not been seen yet, I hold 5+ tarokks, and have one to lead ('+strong+')?',{src:L(483),tag:'pagat_catch'},'yes',T('Lead my highest such tarokk','draw tarokks until the pagát falls')),
    q('Four kings or double game is announced, I am on the enemy team, and I have a suit card?',{src:LS(`if kings_bid and defender and enemy_suit:`)},'yes',S('Lead the cheapest card of a suit whose king I do not hold','keep my own kings away from their tarokks; any suit if I hold every king')),
    q('General rule once four kings or double game is announced: the caller team leads a tarokk. The checks below pick which one.',{rule:true},null,null,'then'),
    q('I am on the enemy team, the skíz or the XXI has already been played, and I have a suit card?',{src:L(489)},'yes',S('Lead the low suit card','nothing left to protect'))
  ] : [
    q('Do I hold the skíz?',{src:L(469),tag:'skiz_hunt'},'yes',hunt()),
    q('A known teammate who plays last to this trick seems to wait with the skíz, I do not hold the XXI, and I have a tarokk beside the pagát?',{src:L(479),tag:'skiz_drive',note:'“Seems to wait”: they threw a XIV–XX under a higher card instead of winning.'},'yes',T('Lead my highest tarokk','drive the XXI out')),
    q('I am on the enemy team, hold neither the skíz nor the XXI, the player who plays last to this trick is a known teammate, and I have a tarokk beside the pagát?',{src:LS(`if protecting and view.is_teammate((view.position + 3) % 4) and plain_tarokks:`)},'yes',T('Lead my lowest tarokk','the teammate\'s XXI can go home in last seat')),
    q('Four kings or double game is announced, I am on the enemy team, and I have a suit card?',{src:LS(`if kings_bid and defender and enemy_suit:`)},'yes',S('Lead the cheapest card of a suit whose king I do not hold','keep my own kings away from their tarokks; any suit if I hold every king')),
    q('General rule once four kings or double game is announced: the caller team leads a tarokk. The checks below pick which one.',{rule:true},null,null,'then'),
    q('I am on the enemy team, hold neither the skíz nor the XXI, and have a suit card?',{src:LS(`if protecting and low_suit:`)},'yes',S('Lead the low suit card','protect a teammate\'s XXI'))
  ];
  const tail=[
    q('A known teammate announced pagát ulti, I have 2+ tarokks beside the pagát, and tarokks are still out?',{src:L(504),tag:'ulti_support'},'yes',T('Lead my second-lowest tarokk','help to draw tarokks, keep the smallest for the end')),
    q('I am on the caller team, hold more than half as many tarokks as are still out, and have one to lead ('+strong+')?',{src:L(511)},'yes',T('Lead my highest such tarokk','draw the tarokks')),
    q('I am on the caller team and have such a tarokk at all?',{src:L(516),tag:'declarer_tarokk'},'yes',T('Lead my lowest such tarokk','the caller team leads a tarokk whenever it has one')),
    q('Do I have a suit card?',{src:L(519)},'yes',S('Lead the low suit card','caller team: from a suit whose king I do not hold, or a king if I hold the king of every suit I have')),
    q('Do I have a tarokk beside the pagát?',{src:L(521)},'yes',T('Lead my lowest tarokk','can be the XXI when nothing else is left')),
    H('Lead the pagát','the only card left')];
  const xxi=q(two?'Exception: the other team announced trull, yet I hold the XXI myself and the skíz is still unplayed?':'Do I hold the XXI?',{src:LS(`if _xxi_at_risk(view):`),note:'Leading the XXI is never safe while the skíz can take it.'},'yes',
    m('Which team am I on?',{src:LS(`if view.on_declarer_side:`)},[
      ['caller team',seq(
        q('My partner has not shown yet, and I hold 3+ tarokks beside the XXI?',{src:LS(`len(view.tarokks) - 1 >= XXI_FIND_PARTNER_TAROKKS`)},'yes',T('Lead my lowest tarokk (not the pagát)','my partner can take it with the called card and show who they are')),
        q('My partner is known, and my tarokks beside the XXI and pagát number more than half of the other tarokks still out (the skíz not counted)?',{src:LS(`elif others and len(others) > (len(out) - 1) / 2`)},'yes',T('Lead my highest tarokk below the XXI','keep leading high tarokks until the skíz has to fall')),
        q('Do I have a suit card?',{src:LS(`if short:`)},'yes',S('Lead the lowest card of my shortest suit whose king I do not hold; a king if I hold the king of every suit I have','soon I can trump that suit; my partner can tell where the king is')),
        G('Carry on with the checks below'))],
      ['enemy team',seq(
        q('Do I have a suit card?',{src:LS(`elif low_suit:`)},'yes',S('Lead the low suit card','a suit, never a tarokk')),
        G('Carry on with the checks below'))]]));
  const drop=q('It is the second-last trick, I hold the pagát and one more card, I did not announce pagát ulti, and more than 3 tarokks are still out?',{src:LS(`if doomed_pagat:`),note:'Count the tarokks: three players can play at most three of them to this trick, so one is left for the last trick and beats the pagát there. That is a lost silent pagát ulti, whoever takes it.'},'yes',H('Lead the pagát','better lost now than as a lost silent ulti in the last trick'));
  return seq(drop,xxi,...mid,...head,...tail);
}

function followTree(two){
  const huntQ = two
    ? 'Exception: the other team announced trull, yet I hold the skíz myself and the XXI is still unplayed?'
    : 'Do I hold the skíz (so I am waiting for the XXI)?';
  const xxiQ = two ? 'Exception: the other team announced trull, yet I hold the XXI myself and the skíz is still unplayed.' : 'I hold the XXI.';
  const drive = two ? ', or (while skíz and XXI are both unplayed) the known teammate seated before me seems to wait with the skíz' : ', or the known teammate seated before me seems to wait with the skíz';
  const mate=seq(
    q('Their card is certain to hold (no opponent after me, or their tarokk beats everything still out), I have the pagát, and I did not announce pagát ulti?',{src:L(593)},'yes',H('Play the pagát','bring it home')),
    q('Not certain, they are winning with a suit card, an opponent plays after me, all I can play are tarokks, and a king is in the trick or my teammate led the suit?',{src:L(595),tag:'hit_hard · hit_hard_lead'},'yes',T('Play a hard tarokk','keep the trick and the lead on our side')),
    q('The trick is certain and I have a suit card?',{src:L(600),tag:'safe_feed'},'yes',S('Play my most valuable suit card','feed the teammate')),
    X('Play my cheapest card'));
  const foe=seq(
    q('I can win, an opponent plays after me, all I can play are tarokks, and a king is in the trick or a known teammate led a suit?',{src:L(611),tag:'hit_hard'},'yes',T('Play a hard tarokk')),
    q('Kurta: I could win, but the trick holds under 5 points, it is one of the first four tricks, I hold 7+ tarokks and a known teammate plays after me?',{src:L(619),tag:'kurta'},'yes',X('Play my cheapest card','leave it to the shorter hand')),
    q('Can I win the trick? (The pagát counts as a winner only when I play last.)',{src:L(606)},'no',X('Play my cheapest card'),'yes'),
    q('Am I the last to play?',{src:L(627)},'yes',seq(
      q('Does the pagát win it?',{src:L(628)},'yes',H('Play the pagát','bring it home')),
      X('Win with my cheapest winning card'))),
    q('Worth it: 5+ points in the trick, or a known opponent is winning it'+drive+'?',{src:L(615),tag:'stop_foe · skiz_drive'},'yes',X('Win with my cheapest winning card')),
    X('Play my cheapest card'));
  const hunt=seq(
    q('A tarokk was led, and no more tarokks are still out than players still to play after me?',{src:LS(`if skiz and lead_card.is_tarokk() and seats_after and len(out) <= len(seats_after):`)},'yes',H('Play the skíz','the XXI has to come, even though it is not in the trick yet')),
    q('I play last, a known teammate is winning the trick, their lead would let the XXI play behind both of us and mine would not, and I can win with a card other than skíz and pagát?',{src:LS(`if ("skiz_take_lead" in TACTICS and not seats_after and view.is_teammate(winner_seat)`),tag:'skiz_take_lead',note:'The XXI goes home when nobody who could hold the skíz plays after it. If I hold the pagát too, the XXI is the declarer’s; otherwise it may be with either opponent.'},'yes',X('Take the trick with my cheapest card that wins','the lead comes to me: the holder of the XXI cannot know which of us has the skíz, so it cannot go home')),
    q('Can I stay under the trick with a card other than skíz and pagát?',{src:LA(`waiting = [c for c in without_pagat if not _is(c, SKIZ)]`,`if losers:`)},'yes',seq(
      q('Are all those losing cards tarokks?',{src:L(572)},'yes',T('Play the highest tarokk that still loses','shed high tarokks, stay out of the lead')),
      q('Is a known teammate winning the trick?',{src:L(574)},'yes',S('Play my most valuable losing card','feed the teammate')),
      X('Play my cheapest losing card'))),
    q('Do I have any card other than skíz and pagát?',{src:L(577)},'yes',X('Play the cheapest of them','forced to win')),
    G('Carry on with the checks below'));
  const trullWin=q('Trull was called, I can win the trick, and my team does not already hold it for certain?',{src:LS(`if can_win and not team_safe:`),note:'General rule once trull is called: every trick is fought for. “For certain” means a known teammate is winning and no opponent can still beat their card.'},'yes',seq(
    q('Does an opponent still play after me?',{src:LA(`if can_win and not team_safe:`,`if foe_after:`)},'yes',seq(
      q('The declarer led, their partner plays right after me, my teammate plays last, and my best card is a tarokk that can still be beaten?',{src:LS(`_declarer_then_me_then_partner(view, trick) and best.is_tarokk()`),tag:'trull_spare',note:'The partner is known from the called card or from having announced something. They have to play high whatever I do, because my teammate still plays after them.'},'yes',G('Carry on with the checks below','no hard tarokk is spent here')),
      X('Win with my best card','a hard tarokk, or my highest card of the suit led; also over a teammate who is winning'))),
    q('Does the pagát win it?',{src:LS(`elif pagat in can_win:`)},'yes',H('Play the pagát','bring it home')),
    X('Win with my cheapest winning card')));
  return seq(
    q('Only one legal card?',{src:L(529)},'yes',X('Play it')),
    q('Working out who must follow suit: my known teammate on the caller team led a low suit card (by our convention not from a suit whose king they hold), I do not hold that king, and all but one of the other players have shown they are out of the suit. That one player holds the king and has to follow suit. Once the trick is trumped, that player does not count as an opponent after me in the checks below.',{rule:true,note:'A king cannot lie in the skart, so it must be in that hand.'},null,null,'then'),
    q(xxiQ+' I may play the XXI, and the only opponent after me is the player who must follow suit with the king?',{src:LS(`if at_risk and xxi and bound is not None and not foe_after:`)},'yes',H('Play the XXI','nobody can put the skíz on it; it comes home, usually with the king')),
    q(xxiQ+' I may play the XXI, and nobody but known teammates plays after me (or I am last)?',{src:LS(`if at_risk and xxi and not foe_after:`)},'yes',H('Play the XXI','it escapes: nobody left to play can hold the skíz against me')),
    q('I can play the skíz, and the XXI of somebody not known as my teammate lies in the trick?',{src:L(539)},'yes',H('Play the skíz','XXI caught')),
    q('It is the second-last trick, I hold the pagát and one more card, both are legal, I did not announce pagát ulti, and more tarokks are still out than players still to play after me?',{src:LA(`doomed_pagat = _pagat_must_go(view, len(seats_after))`,`if doomed_pagat:`),note:'Count the tarokks: one is left for the last trick and beats the pagát there. That is a lost silent pagát ulti, whoever takes it.'},'yes',H('Play the pagát','better lost now than as a lost silent ulti in the last trick')),
    q('I hold the called card but neither the skíz nor the XXI, the declarer led a tarokk, an opponent plays after me, and my called card would take over the trick?',{src:L(547),tag:'show_called'},'yes',T('Play the called card','shows the table who is with whom')),
    q('Set aside before choosing (if another card is legal): the XXI, while the skíz is in another hand and an opponent plays after me; the pagát, if I announced pagát ulti.',{src:L(553),rule:true},null,null,'then'),
    q(xxiQ+' An opponent plays after me, and I have a card (not the XXI, not the pagát) that does not win the trick?',{src:LS(`if at_risk and foe_after:`)},'yes',X('Play my cheapest card that does not win','stay out of the lead; if the player after me takes the trick, I play last to the next one')),
    q(huntQ,{src:L(568),tag:'skiz_hunt'},'yes',hunt),
    ...(two?[trullWin]:[]),
    m('Who is winning the trick so far?',{src:L(588)},[['a known teammate',mate],['an opponent, or somebody whose side I do not know',foe]]));
}

// ---- D: skart ---------------------------------------------------------------
const SK=seq(
  q('Did I give the invit? Then the card I invited with is never discarded.',{src:L(170),rule:true},null,null,'then'),
  q('I hold the skíz without the XXI and more than 6 tarokks, and I do not expect to be called (I hold no XX, and the bid winner did not take my invit)?',{src:L(189),tag:'skiz_weak_skart'},'yes',T('Discard my highest allowed tarokks first, until 6 tarokks are left','a skíz hoping to catch the XXI wants to stay out of the lead; any discards still owed follow the checks below')),
  m('Whose team does my skart count for?',{src:LS(`cheap_first = `),tag:'xx_cheap_skart'},[
    ['I won the bidding',S('Suit cards: kingless suits first, shortest suit first, dearest card first. Then tarokks, lowest first.','my skart counts for my own team: put points into it')],
    ['I expect to be called: I hold the XX, or the bid winner took my invit',S('Suit cards: kingless suits first, shortest suit first, cheapest card first. Then tarokks, lowest first.','my skart counts for the enemy team: give away as little as possible')],
    ['anybody else',S('Suit cards: kingless suits first, shortest suit first, dearest card first. Then tarokks, lowest first.','my skart counts for the enemy team, which I expect to be on: put points into it')]]));

// ---- numbering --------------------------------------------------------------
// Every box gets its number here, in reading order: a check, then what hangs to its right, then what follows below.
function number(roots,prefix,start){
  let n=start||0;
  const visit=node=>{
    let cur=node;
    while(cur){
      cur.id=prefix+(++n);
      if(cur.leaf)break;
      for(const [,child] of cur.right)visit(child);
      cur=cur.down?cur.down[1]:null;
    }
  };
  roots.forEach(visit);
  return n;
}
const TREES={
  A:[A,A2], B1:[B1], B2:[B2], B3:[B3],
  C0:[C0], CIlead:[leadTree(false)], CIfollow:[followTree(false)], CIIlead:[leadTree(true)], CIIfollow:[followTree(true)],
  D:[SK],
};
number(TREES.A,'A');
number(TREES.B3,'B',number(TREES.B2,'B',number(TREES.B1,'B')));
number(TREES.CIIfollow,'C',number(TREES.CIIlead,'C',number(TREES.CIfollow,'C',number(TREES.CIlead,'C',number(TREES.C0,'C')))));
number(TREES.D,'D');

// ---- for the server: which source line is which box -------------------------
// {line: [{id, yes, no}]}: "yes" is the action box right of a check, "no" the action box below it
function collect(roots){
  const out={};
  const leafId=node=>node&&node.leaf&&node.leaf!=='goto'?node.id:null;
  const visit=node=>{
    let cur=node;
    while(cur&&!cur.leaf){
      const m=/:(\d+)$/.exec(cur.src||'');
      if(m)(out[m[1]]=out[m[1]]||[]).push({id:cur.id,yes:cur.right.length===1?leafId(cur.right[0][1]):null,no:cur.down?leafId(cur.down[1]):null});
      for(const [,child] of cur.right)visit(child);
      cur=cur.down?cur.down[1]:null;
    }
  };
  roots.forEach(visit);
  return out;
}
const team=i=>Object.assign(collect([TREES.B2[0].right[i][1]]),collect(TREES.B3));
const CONTEXTS={
  A:collect(TREES.A), B1:collect(TREES.B1),
  'B.declarer':team(0), 'B.partner':team(1), 'B.enemy':team(2),
  'C.I':collect([...TREES.CIlead,...TREES.CIfollow]), 'C.II':collect([...TREES.CIIlead,...TREES.CIIfollow]),
  D:collect(TREES.D),
};

// ---- drawing ----------------------------------------------------------------
// Texts are written in English above; hu.js holds the Hungarian for each of them, word for word as the key
let LANG='en';
const tr=s=>(LANG==='hu'&&HU[s])||s;
function el(tag,cls,html){const e=document.createElement(tag);if(cls)e.className=cls;if(html!=null)e.innerHTML=html;return e}
const idTag=node=>'<span class="id">'+node.id+'</span>';
function leafEl(node){
  return el('div','leaf k-'+node.leaf,idTag(node)+tr(node.text)+(node.detail?'<small>'+tr(node.detail)+'</small>':''));
}
function render(node){
  if(node.leaf)return leafEl(node);
  const chain=el('div','chain');
  let cur=node;
  while(cur){
    if(cur.leaf){chain.appendChild(leafEl(cur));break}
    const step=el('div','step');
    let meta='';
    if(cur.tag||cur.src)meta='<div class="meta">'+(cur.tag?'<span class="tag">'+cur.tag+'</span>':'')+(cur.src?'<span>'+cur.src+'</span>':'')+'</div>';
    step.appendChild(el('div','node'+(cur.rule?' rule':''),idTag(cur)+tr(cur.text)+(cur.note?'<span class="note">'+tr(cur.note)+'</span>':'')+meta));
    if(cur.right.length){
      const bs=el('div','branches');
      for(const [label,child] of cur.right){
        const b=el('div','branch');
        b.appendChild(el('div','edge','<span>'+tr(label)+'</span>'));
        b.appendChild(render(child));
        bs.appendChild(b);
      }
      step.appendChild(bs);
    }
    chain.appendChild(step);
    if(!cur.down)break;
    chain.appendChild(el('div','down',tr(cur.down[0])+' ↓'));
    cur=cur.down[1];
  }
  return chain;
}
function mount(target,roots){
  const box=el('div','chain');box.style.gap='18px';
  roots.forEach(r=>box.appendChild(render(r)));
  const host=document.getElementById(target);
  host.textContent='';
  host.appendChild(box);
}
// Every text a tree shows, for the build to check that hu.js covers all of them
function strings(){
  const out=new Set();
  const visit=node=>{
    let cur=node;
    while(cur){
      out.add(cur.text);
      for(const extra of [cur.detail,cur.note])if(extra)out.add(extra);
      if(cur.leaf)break;
      for(const [label,child] of cur.right){if(label)out.add(label);visit(child)}
      if(!cur.down)break;
      out.add(cur.down[0]);
      cur=cur.down[1];
    }
  };
  Object.values(TREES).forEach(roots=>roots.forEach(visit));
  return [...out];
}
function show(lang){
  LANG=lang==='hu'?'hu':'en';
  document.documentElement.lang=LANG;
  for(const e of document.querySelectorAll('[data-t]')){
    if(e.dataset.en===undefined)e.dataset.en=e.innerHTML;
    e.innerHTML=(LANG==='hu'&&PAGE_HU[e.dataset.t])||e.dataset.en;
  }
  document.title=LANG==='hu'?PAGE_HU.title:'Tarokk Bot Decision Trees';
  for(const a of document.querySelectorAll('[data-lang]'))a.setAttribute('aria-current',a.dataset.lang===LANG?'true':'false');
  mount('treeA',TREES.A);mount('treeB1',TREES.B1);mount('treeB2',TREES.B2);mount('treeB3',TREES.B3);
  mount('treeC0',TREES.C0);mount('treeC1',TREES.CIlead);mount('treeC2',TREES.CIfollow);mount('treeC3',TREES.CIIlead);mount('treeC4',TREES.CIIfollow);
  mount('treeS',TREES.D);
}
if(typeof document==='undefined'){
  module.exports={CONTEXTS,TREES,HU,PAGE_HU,STRINGS:strings()};
}else{
  // ?lang=hu from the app's link; otherwise what was picked here last time, then the browser's language
  let lang=new URLSearchParams(location.search).get('lang');
  try{lang=lang||localStorage.getItem('treeLang')}catch(e){}
  lang=lang||(navigator.language||'en').slice(0,2);
  for(const a of document.querySelectorAll('[data-lang]'))a.addEventListener('click',event=>{
    event.preventDefault();
    try{localStorage.setItem('treeLang',a.dataset.lang)}catch(e){}
    show(a.dataset.lang);
  });
  show(lang);
}
