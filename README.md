# pyRCV

Standalone Python 3 scripts for counting various preferential voting elections, including:

* [Wright STV](http://www.aph.gov.au/Parliamentary_Business/Committees/House_of_Representatives_Committees?url=/em/elect07/subs/sub051.1.pdf)
* Single Transferable Vote (weighted inclusive Gregory)
* Instant Runoff Voting (aka. the Alternative Vote)

Like preferential voting? Why not check out [helios-server-mixnet](https://github.com/RunasSudo/helios-server-mixnet), an end-to-end voter verifiable online voting system which supports preferential voting?

## irv.py

    ./irv.py election.blt

Takes as input an [OpenSTV blt file](https://stackoverflow.com/questions/2233695/how-do-i-generate-blt-files-for-openstv-elections-using-c), and calculates the winner under IRV.

Supply the `--npr` option to use non-proportional representation, iteratively removing the winner from each round to produce an ordered list of winners – as for the filling of casual vacancies.

## stv.py, wright_stv.py

    ./stv.py election.blt
    ./wright_stv.py election.blt

Takes as input an [OpenSTV blt file](https://stackoverflow.com/questions/2233695/how-do-i-generate-blt-files-for-openstv-elections-using-c), and calculates the winners under STV/Wright STV.

### Performing a countback
These scripts can be used to perform a Hare-Clark-style countback to fill vacancies. Firstly, we must capture the quota of votes used to finally elect the candidate causing the vacancy:

    ./wright_stv.py election.blt --countback CandidateName countback.blt

This command will output a new blt file containing only this quota of votes. We can then run an instant-runoff election with these votes.

    ./irv.py countback.blt

If some candidates have chosen not to contest the countback, you can add an `-ID` line into the blt file in the withdrawn candidates block, where `ID` is the 1-indexed position of the candidate in the candidate list.
