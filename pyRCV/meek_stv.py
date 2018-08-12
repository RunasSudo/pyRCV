#!/usr/bin/env python
#    Copyright © 2016-2018 RunasSudo (Yingtong Li)
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

import itertools

from .utils import common
from .stv import STVResult
from . import stv
from . import utils
from . import version

class MeekSTVCounter(stv.STVCounter):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		for candidate in self.candidates:
			candidate.keep_value = utils.numclass('1')
	
	def resetCount(self, ballots, candidates):
		for candidate in candidates:
			candidate.ctvv = utils.numclass('0')
			candidate.ballots.clear()
	
	def distributePreferences(self, ballots, remainingCandidates):
		exhausted = utils.numclass('0')
		
		for ballot in ballots:
			assigned = utils.numclass('0')
			last_preference = None
			for preference in ballot.preferences:
				if preference.keep_value > utils.numclass('0'):
					value = (ballot.value - assigned) * preference.keep_value
					
					self.verboseLog('   - Assigning {} of {} votes to {} at value {} via {}', self.toNum(ballot.value - assigned), self.toNum(ballot.value), preference.name, self.toNum(preference.keep_value), ballot.prettyPreferences)
					
					preference.ctvv += value
					assigned += value
					preference.ballots.append(common.CandidateBallot(ballot, value))
				
				if assigned >= ballot.value:
					break
			
			if assigned < ballot.value:
				self.verboseLog('   - Exhausted {} votes via {}', self.toNum(ballot.value - assigned), ballot.prettyPreferences)
				exhausted += ballot.value - assigned
		
		return exhausted
	
	def calcQuota(self, remainingCandidates):
		# Adjust quota according to excess, i.e. use total vote
		return self.calcQuotaNum(self.totalVote(remainingCandidates), self.args['seats'])
	
	def countUntilExclude(self, remainingCandidates, provisionallyElected):
		roundProvisionallyElected = []
		roundExhausted = utils.numclass('0')
		
		self.printVotes(remainingCandidates, provisionallyElected)
		
		quota = self.calcQuota(remainingCandidates)
		
		self.infoLog('---- Total Votes: {}', self.toNum(self.totalBallots))
		self.infoLog('----   Of which not exhausted: {}', self.toNum(self.totalVote(remainingCandidates)))
		self.infoLog('----   Of which exhausted: {}', self.toNum(self.exhausted + roundExhausted))
		self.infoLog('---- Quota: {}', self.toNum(quota))
		self.infoLog()
		
		remainingCandidates.sort(key=lambda k: k.ctvv, reverse=True)
		for candidate in remainingCandidates:
			if candidate not in (provisionallyElected + roundProvisionallyElected) and self.hasQuota(candidate, quota):
				self.infoLog("**** {} provisionally elected", candidate.name)
				roundProvisionallyElected.append(candidate)
		
		if self.args.get('fast', False) and (len(provisionallyElected) + len(roundProvisionallyElected)) >= self.args['seats']:
			return STVResult([], roundProvisionallyElected, roundExhausted, {cand: cand.ctvv for cand in remainingCandidates})
		
		mostVotesElected = sorted(roundProvisionallyElected, key=lambda k: k.ctvv, reverse=True)
		self.infoLog('   - Distributing surpluses')
		# While surpluses remain
		while mostVotesElected and any(abs(c.ctvv - quota) > utils.numclass('0.00001') for c in mostVotesElected):
			# Recalculate weights
			for candidate in mostVotesElected:
				self.verboseLog('     Reducing {} keep value from {} to {}', candidate.name, self.toNum(candidate.keep_value), self.toNum(candidate.keep_value * quota / candidate.ctvv))
				candidate.keep_value *= quota / candidate.ctvv
			
			# Redistribute votes
			#for candidate in remainingCandidates:
			#	candidate.ctvv = utils.numclass('0')
			#	candidate.ballots.clear()
			self.resetCount(self.ballots, remainingCandidates)
			roundExhausted = self.distributePreferences(self.ballots, remainingCandidates)
			
			quota = self.calcQuota(remainingCandidates)
			
			# Check again for election
			remainingCandidates.sort(key=lambda k: k.ctvv, reverse=True)
			for candidate in remainingCandidates:
				if candidate not in (provisionallyElected + roundProvisionallyElected) and self.hasQuota(candidate, quota):
					self.infoLog("**** {} provisionally elected", candidate.name)
					roundProvisionallyElected.append(candidate)
			
			if self.args.get('fast', False) and (len(provisionallyElected) + len(roundProvisionallyElected)) >= self.args['seats']:
				return STVResult([], roundProvisionallyElected, roundExhausted, {cand: cand.ctvv for cand in remainingCandidates})
			
			mostVotesElected = sorted(roundProvisionallyElected, key=lambda k: k.ctvv, reverse=True)
		
		if (len(provisionallyElected) + len(roundProvisionallyElected)) >= self.args['seats']:
			return STVResult([], roundProvisionallyElected, roundExhausted, {cand: cand.ctvv for cand in remainingCandidates})
		
		self.printVotes(remainingCandidates, provisionallyElected)
		
		# We only want to do this after preferences have been distributed
		if not self.args.get('fast', False) and len(remainingCandidates) <= self.args['seats']:
			remainingCandidates.sort(key=lambda k: k.ctvv, reverse=True)
			for candidate in remainingCandidates:
				if candidate not in (provisionallyElected + roundProvisionallyElected):
					self.infoLog('**** {} provisionally elected on {} quotas', candidate.name, self.toNum(candidate.ctvv / quota))
					roundProvisionallyElected.append(candidate)
			return STVResult([], roundProvisionallyElected, roundExhausted, {cand: cand.ctvv for cand in remainingCandidates})
		
		# Bulk exclude as many candidates as possible
		remainingCandidates.sort(key=lambda k: k.ctvv)
		grouped = [(x, list(y)) for x, y in itertools.groupby([x for x in remainingCandidates if x not in (provisionallyElected + roundProvisionallyElected)], lambda k: k.ctvv)] # ily python
		
		votesToExclude = utils.numclass('0')
		for i in range(0, len(grouped)):
			key, group = grouped[i]
			votesToExclude += self.totalVote(group)
		
		candidatesToExclude = []
		for i in reversed(range(0, len(grouped))):
			key, group = grouped[i]
			
			# Would the total number of votes to exclude geq the next lowest candidate?
			if len(grouped) > i + 1 and votesToExclude >= float(grouped[i + 1][0]):
				votesToExclude -= self.totalVote(group)
				continue
			
			# Would the total number of votes to exclude allow a candidate to reach the quota?
			lowestShortfall = float('inf')
			for candidate in remainingCandidates:
				if candidate not in (provisionallyElected + roundProvisionallyElected) and (quota - candidate.ctvv < lowestShortfall):
					lowestShortfall = quota - candidate.ctvv
			if votesToExclude >= lowestShortfall:
				votesToExclude -= self.totalVote(group)
				continue
			
			# Still here? Okay!
			candidatesToExclude = []
			for j in range(0, i + 1):
				key, group = grouped[j]
				candidatesToExclude.extend(group)
		
		if candidatesToExclude:
			for candidate in candidatesToExclude:
				self.infoLog('---- Bulk excluding {}', candidate.name)
			return STVResult(candidatesToExclude, roundProvisionallyElected, roundExhausted, {cand: cand.ctvv for cand in remainingCandidates})
		else:
			# Just exclude one candidate then
			# Check for a tie
			if len(remainingCandidates) > 1 and remainingCandidates[0].ctvv == remainingCandidates[1].ctvv:
				# There is a tie. Can we break it?
				toExclude = None
				
				tiedCandidates = [x for x in remainingCandidates if x.ctvv == remainingCandidates[0].ctvv]
				
				self.log("---- There is a tie for last place:")
				for i in range(0, len(tiedCandidates)):
					self.log("     {}. {}".format(i, tiedCandidates[i].name))
				
				tie_methods = iter(self.args.get('ties', ['manual']))
				
				while toExclude is None:
					tie_method = next(tie_methods, None)
					if tie_method is None:
						self.log("---- No resolution for tie, and no further tie-breaking methods specified")
						self.log("---- Tie enable manual breaking of ties, append 'manual' to the --ties option")
						return False
					
					if tie_method == 'backward':
						# Was there a previous round where any tied candidate was behind the others?
						for previous_tally in reversed(self.tally_history):
							prev_tally_min = min(prev_ctvv for cand, prev_ctvv in previous_tally.items() if cand in tiedCandidates)
							prev_lowest = [cand for cand, prev_ctvv in previous_tally.items() if prev_ctvv == prev_tally_min]
							if len(prev_lowest) == 1:
								self.log("---- Tie broken backwards")
								toExclude = remainingCandidates.index(prev_lowest[0])
								break # inner for
					
					if tie_method == 'random':
						self.log("---- Tie broken randomly")
						max_byte = (256 // len(tiedCandidates)) * len(tiedCandidates)
						self.log("     Getting random byte {}".format(self.randbyte))
						while self.randdata[self.randbyte] >= max_byte:
							self.randbyte += 1
							self.log("     Getting random byte {}".format(self.randbyte))
						toExclude = remainingCandidates.index(tiedCandidates[self.randdata[self.randbyte] % len(tiedCandidates)])
						self.log("     Byte {} is {}, mod {} is {}".format(self.randbyte, self.randdata[self.randbyte], len(tiedCandidates), toExclude))
						self.randbyte += 1
					
					if tie_method == 'manual':
						self.log("---- No resolution for tie")
						self.log("---- Which candidate to exclude?")
						toExclude = remainingCandidates.index(tiedCandidates[int(input())])
			else:
				# No tie. Exclude the lowest candidate
				toExclude = 0
			
			self.infoLog('---- Excluding {}', remainingCandidates[toExclude].name)
			return STVResult([remainingCandidates[toExclude]], roundProvisionallyElected, roundExhausted, {cand: cand.ctvv for cand in remainingCandidates})
	
	def countVotes(self):
		self.totalBallots = self.totalVoteBallots(self.ballots)
		
		count = 1
		remainingCandidates = self.candidates[:]
		provisionallyElected = []
		
		while True:
			self.infoLog()
			self.infoLog("== COUNT {}".format(count))
			
			self.resetCount(self.ballots, remainingCandidates)
			self.exhausted = self.distributePreferences(self.ballots, remainingCandidates)
			
			roundResult = self.countUntilExclude(remainingCandidates, provisionallyElected)
			
			# Process round
			
			self.exhausted += roundResult.exhausted
			
			if roundResult.excluded:
				# Reset and reiterate
				for candidate in roundResult.excluded:
					candidate.keep_value = utils.numclass('0')
					remainingCandidates.remove(candidate)
				
				if self.args['fast'] and len(remainingCandidates) <= self.args['seats']:
					remainingCandidates.sort(key=lambda k: k.ctvv, reverse=True)
					for candidate in remainingCandidates:
						if candidate not in provisionallyElected:
							print("**** {} provisionally elected on {} votes".format(candidate.name, self.toNum(candidate.ctvv)))
							provisionallyElected.append(candidate)
					return provisionallyElected, self.exhausted
				
				count += 1
				continue
			
			# We must be done!
			
			for candidate in roundResult.provisionallyElected:
				provisionallyElected.append(candidate)
			
			return provisionallyElected, self.exhausted
	
	@classmethod
	def main(cls):
		from .utils import blt
		
		print('=== pyRCV {} ==='.format(version.VERSION))
		print()
		
		parser = cls.getParser()
		args = parser.parse_args()
		
		if args.float:
			utils.numclass = float
		
		# Read blt
		with open(args.election, 'r') as electionFile:
			electionLines = electionFile.read().splitlines()
			ballots, candidates, args.seats = blt.readBLT(electionLines)
		
		counter = cls(ballots, candidates, **vars(args))
		
		if args.verbose:
			for ballot in ballots:
				print("{} : {}".format(counter.toNum(ballot.value), ",".join([x.name for x in ballot.preferences])))
			print()
		
		elected, exhausted = counter.countVotes()
		print()
		print("== TALLY COMPLETE")
		print()
		print("The winners are, in order of election:")
		
		elected.sort(key=lambda x: x.keep_value)
		
		print()
		for candidate in elected:
			print("     {} ({})".format(candidate.name, counter.toNum(candidate.keep_value)))
		print()
		
		print("---- Exhausted: {}".format(counter.toNum(exhausted)))
		
		if args.countback:
			candidate = next(x for x in candidates if x.name == args.countback[0])
			print("== STORING COUNTBACK DATA FOR {}".format(candidate.name))
			
			# Sanity check
			ctvv = 0
			for ballot in candidate.ballots:
				ctvv += ballot.value
			assert ctvv == candidate.ctvv
			
			candidatesToExclude = []
			for peCandidate in provisionallyElected:
				candidatesToExclude.append(peCandidate)
			
			with open(args.countback[1], 'w') as countbackFile:
				# use --noround to determine whether to use standard BLT format or rational BLT format
				stringify = str if args.noround else float
				print('\n'.join(utils.blt.writeBLT(candidate.ballots, candidates, 1, '', candidatesToExclude, stringify)), file=countbackFile)
		
		print()
		print("=== Tally computed by pyRCV {} ===".format(version.VERSION))

if __name__ == '__main__':
	MeekSTVCounter.main()