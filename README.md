# pyRCV

Standalone Python 3 scripts for counting various preferential voting elections, including:

* [Wright STV](http://www.aph.gov.au/Parliamentary_Business/Committees/House_of_Representatives_Committees?url=/em/elect07/subs/sub051.1.pdf)
* Single Transferable Vote (weighted inclusive Gregory)
* Instant Runoff Voting (aka. the Alternative Vote)

Like preferential voting? Why not check out [helios-server-mixnet](https://github.com/RunasSudo/helios-server-mixnet), an end-to-end voter verifiable online voting system which supports preferential voting?

## irv.py

    python -m pyRCV.irv --election election.blt

Takes as input an [OpenSTV blt file](https://stackoverflow.com/questions/2233695/how-do-i-generate-blt-files-for-openstv-elections-using-c), and calculates the winner under IRV.

Supply the `--npr` option to use non-proportional representation, iteratively removing the winner from each round to produce an ordered list of winners – as for the filling of casual vacancies.

## stv.py

    python -m pyRCV.stv --election election.blt

Takes as input an [OpenSTV blt file](https://stackoverflow.com/questions/2233695/how-do-i-generate-blt-files-for-openstv-elections-using-c), and calculates the winners under STV.

The counting method is highly configurable to a wide range of STV implementations. See `./stv.py --help` for more information.

### wright_stv.py

    python -m pyRCV.wright_stv --election election.blt --quota-prog

The same for Wright STV. Note that Wright STV uses a progressively-reducing quota, so `--quota-prog` should be specified.

### meek_stv.py

    python -m pyRCV.meek_stv --election election.blt --quota geq-hb --quota-prog --nums float

The same for Meek STV. Note that Meek STV uses a progressively-reducing quota (`--quota-prog`), and the quota is the unrounded Droop (Hagenbach-Bischoff) quota (`--quota geq-hb`). Note also that Meek STV is quite computationally expensive, so the `--nums float` option is recommended to disable rational arithmetic.

### Performing a countback

These scripts can be used to perform a Hare-Clark-style countback to fill vacancies. Firstly, we must capture the quota of votes used to finally elect the candidate causing the vacancy:

    python -m pyRCV.wright_stv --election election.blt --countback CandidateName countback.blt

This command will output a new blt file containing only this quota of votes. We can then run an instant-runoff election with these votes.

    python -m pyRCV.irv --election countback.blt

If some candidates have chosen not to contest the countback, you can add an `-ID` line into the blt file in the withdrawn candidates block, where `ID` is the 1-indexed position of the candidate in the candidate list.

### Performance metrics

On an HP Pavilion dv7-6108tx, the 49,702-vote [EVE Online CSM8 election](https://community.eveonline.com/news/dev-blogs/csm8-election-statistics/) is processed by the EVE Online [reference implementation](http://cdn1.eveonline.com/community/csm/CSM11_Election.zip) of Wright STV in an average of 6.37 seconds. (±0.04s) The same election is processed by pyRCV's equivalent `wright_stv.py --fast --nums float --noround` in an average of **2.34 seconds!** (±0.02s) For comparison, using increased-accuracy rational arithmetic (omitting `--num float`) takes an average of 8.64 seconds. (±0.04s)
