#!/usr/bin/env python
#    Copyright © 2016 RunasSudo (Yingtong Li)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

# I love the smell of Python 3 in the morning

from . import stv

class IRVCounter(stv.STVCounter):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self.args['seats'] = 1
	
	def calcQuota(self, remainingCandidates):
		return self.calcQuotaNum(self.totalVote(remainingCandidates), self.args['seats'])
	
	@classmethod
	def getParser(cls):
		import argparse
		
		parser = super().getParser()
		parser.add_argument('--quota', help=argparse.SUPPRESS, default='gt-hb')
		parser.add_argument('--countback', help=argparse.SUPPRESS)
		parser.add_argument('--npr', help='Generate a list of winners', action='store_true')
		
		return parser
	
	@classmethod
	def main(cls):
		from .utils import blt
		
		parser = cls.getParser()
		args = parser.parse_args()
		
		# Read blt
		with open(args.election, 'r') as electionFile:
			electionLines = electionFile.read().splitlines()
			ballots, candidates, args.seats = blt.readBLT(electionLines)
		
		counter = cls(ballots, candidates, **vars(args))
		
		if args.verbose:
			for ballot in ballots:
				print("{} : {}".format(counter.toNum(ballot.value), ",".join([x.name for x in ballot.preferences])))
		
		nprElected = []
		for i in range(0, len(candidates) if args.npr else 1):
			print("== ITERATION {}".format(i + 1))
			elected, exhausted = counter.countVotes()
			nprElected.extend(elected)
			counter.candidates.remove(elected[0])
		
		print()
		print("== TALLY COMPLETE")
		print()
		print("The winners are, in order of election:")
		
		print()
		for candidate in nprElected:
			print("     {}".format(candidate.name))
		print()
		
		if not args.npr:
			print("---- Exhausted: {}".format(counter.toNum(exhausted)))

if __name__ == '__main__':
	IRVCounter.main()
