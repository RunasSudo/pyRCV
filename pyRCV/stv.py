#!/usr/bin/env python
#    Copyright © 2016-2019 RunasSudo (Yingtong Li)
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

from .utils import common
from . import utils
from . import version

import base64
import itertools
import json
import math

# Represents the outcome of the current round
class STVResult:
	def __init__(self, excluded, provisionallyElected, exhausted, tally):
		self.excluded = excluded
		self.provisionallyElected = provisionallyElected
		self.exhausted = exhausted
		self.tally = tally

class STVCounter:
	def __init__(self, ballots, candidates, **kwargs):
		self.args = kwargs
		
		self.ballots = ballots
		self.candidates = candidates
		
		self.exhausted = utils.num('0')
		
		self.randdata = None
		self.randbyte = 0
		if self.args.get('randfile', None):
			with open(self.args['randfile'], 'r') as f:
				self.randdata = base64.b64decode(json.load(f)['result']['random']['data'][0])
			if self.args.get('randbyte', None):
				self.randbyte = int(self.args['randbyte'])
		
		self.tally_history = []
	
	def log(self, string='', *args):
		print(string.format(*args))
	
	def verboseLog(self, string='', *args):
		if self.args.get('verbose', False):
			self.log(string, *args)
	
	def infoLog(self, string='', *args):
		if not self.args.get('quiet', False):
			self.log(string, *args)
	
	def resetCount(self, candidates):
		for candidate in candidates:
			candidate.ctvv = utils.num('0')
			candidate.ballots.clear()
	
	def distributePreferences(self, ballots, remainingCandidates):
		exhausted = utils.num('0')
		
		for ballot in ballots:
			assigned = utils.num('0')
			last_preference = None
			for preference in ballot.preferences:
				if preference in self.candidates and preference.keep_value > utils.num('0'):
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
	
	def toNum(self, num):
		if self.args.get('noround', False):
			return str(num)
		else:
			return "{:.2f}".format(float(num))
	
	def totalVoteBallots(self, ballots):
		tv = utils.num('0')
		for ballot in ballots:
			tv += ballot.value
		return tv
	
	def totalVote(self, candidates):
		tv = utils.num('0')
		for candidate in candidates:
			tv += candidate.ctvv
		return tv
	
	def calcQuotaNum(self, totalVote, numSeats):
		if '-hb' in self.args['quota']:
			return totalVote / (numSeats + utils.num('1'))
		if '-droop' in self.args['quota']:
			return utils.num(math.floor(totalVote / (numSeats + utils.num('1')) + utils.num('1')))
	
	def calcQuota(self, remainingCandidates):
		if self.args['quota_prog']:
			return self.calcQuotaNum(self.totalVote(remainingCandidates), self.args['seats'])
		else:
			return self.calcQuotaNum(self.totalBallots, self.args['seats'])
	
	def hasQuota(self, candidate, quota):
		if 'gt-' in self.args['quota']:
			return candidate.ctvv > quota
		if 'geq-' in self.args['quota']:
			return candidate.ctvv >= quota
	
	# Return the candidate to transfer votes to for surpluses or exclusion
	def surplusTransfer(self, preferences, fromCandidate, provisionallyElected, remainingCandidates):
		beginPreference = preferences.index(fromCandidate)
		for index in range(beginPreference + 1, len(preferences)):
			preference = preferences[index]
			if preference in remainingCandidates and preference not in provisionallyElected:
				return preference
		return False
	
	def printVotes(self, remainingCandidates, provisionallyElected):
		remainingCandidates.sort(key=lambda k: k.ctvv, reverse=True)
		self.infoLog()
		for candidate in remainingCandidates:
			self.infoLog('    {}{}: {}', '*' if candidate in provisionallyElected else ' ', candidate.name, self.toNum(candidate.ctvv))
		self.infoLog()
	
	def countUntilSurpluses(self, remainingCandidates, provisionallyElected):
		roundProvisionallyElected = []
		roundExhausted = utils.num('0')
		
		self.printVotes(remainingCandidates, provisionallyElected)
		
		quota = self.calcQuota(remainingCandidates)
		
		self.infoLog('---- Total Votes: {}', self.toNum(self.totalBallots))
		self.infoLog('----   Of which not exhausted: {}', self.toNum(self.totalVote(remainingCandidates)))
		self.infoLog('----   Of which exhausted: {}', self.toNum(self.exhausted + roundExhausted))
		self.infoLog('---- Quota: {}', self.toNum(quota))
		self.infoLog()
		
		remainingCandidates.sort(key=lambda k: k.ctvv, reverse=True)
		
		# If "slow" IRV, skip this step, otherwise continue
		if self.args.get('fast', False) or self.args['seats'] > 1:
			for candidate in remainingCandidates:
				if candidate not in (provisionallyElected + roundProvisionallyElected) and self.hasQuota(candidate, quota):
					self.infoLog("**** {} provisionally elected", candidate.name)
					roundProvisionallyElected.append(candidate)
		
		return quota, roundProvisionallyElected, roundExhausted
	
	def countDistributeSurpluses(self, remainingCandidates, provisionallyElected, quota, roundProvisionallyElected):
		mostVotesElected = sorted(roundProvisionallyElected, key=lambda k: k.ctvv, reverse=True)
		# While surpluses remain
		while mostVotesElected and mostVotesElected[0].ctvv > quota:
			for candidate in mostVotesElected:
				if candidate.ctvv > quota:
					multiplier = (candidate.ctvv - quota) / candidate.ctvv
					self.infoLog('---- Transferring surplus from {} at value {}', candidate.name, self.toNum(multiplier))
					
					for ballot in candidate.ballots:
						transferTo = self.surplusTransfer(ballot.ballot.preferences, candidate, provisionallyElected + roundProvisionallyElected, remainingCandidates)
						if transferTo == False:
							self.verboseLog('   - Exhausted {} votes via {}', self.toNum(ballot.value), ballot.ballot.prettyPreferences)
							ballot.value *= (1 - multiplier)
							# roundExhausted += ballot.value * multiplier
							# Since it retains its value and remains in the count, we will not count it as exhausted.
						else:
							self.verboseLog('   - Transferring {} votes to {} via {}', self.toNum(ballot.value), transferTo.name, ballot.ballot.prettyPreferences)
							newBallot = common.CandidateBallot(ballot.ballot, ballot.value * multiplier)
							ballot.value *= (1 - multiplier)
							transferTo.ctvv += newBallot.value
							transferTo.ballots.append(newBallot)
					
					candidate.ctvv = quota
					
					self.printVotes(remainingCandidates, provisionallyElected + roundProvisionallyElected)
					
					for candidate in remainingCandidates:
						if candidate not in (provisionallyElected + roundProvisionallyElected) and self.hasQuota(candidate, quota):
							self.infoLog('**** {} provisionally elected', candidate.name)
							roundProvisionallyElected.append(candidate)
					
					if self.args.get('fast', False) and (len(provisionallyElected) + len(roundProvisionallyElected)) >= self.args['seats']:
						return roundProvisionallyElected
			mostVotesElected = sorted(roundProvisionallyElected, key=lambda k: k.ctvv, reverse=True)
		
		return roundProvisionallyElected
	
	def countUntilExclude(self, remainingCandidates, provisionallyElected):
		quota, roundProvisionallyElected, roundExhausted = self.countUntilSurpluses(remainingCandidates, provisionallyElected)
		
		if self.args.get('fast', False) and (len(provisionallyElected) + len(roundProvisionallyElected)) >= self.args['seats']:
			return STVResult([], roundProvisionallyElected, roundExhausted, {cand: cand.ctvv for cand in remainingCandidates})
		
		roundProvisionallyElected = self.countDistributeSurpluses(remainingCandidates, provisionallyElected, quota, roundProvisionallyElected)
		
		if self.args.get('fast', False) and (len(provisionallyElected) + len(roundProvisionallyElected)) >= self.args['seats']:
			return STVResult([], roundProvisionallyElected, roundExhausted, {cand: cand.ctvv for cand in remainingCandidates})
		
		# Elect all remaining candidates if applicable
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
		
		votesToExclude = utils.num('0')
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
					
					if tie_method == 'all':
						if len(remainingCandidates) - len(tiedCandidates) < self.args['seats']:
							self.log("---- Unable to exclude all tied candidates")
						else:
							self.log("---- Excluding all tied candidates")
							for candidate in tiedCandidates:
								self.infoLog('---- Excluding {}', candidate.name)
							return STVResult(tiedCandidates, roundProvisionallyElected, roundExhausted, {cand: cand.ctvv for cand in remainingCandidates})
					
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
		elected = []
		
		self.resetCount(remainingCandidates)
		self.exhausted = self.distributePreferences(self.ballots, remainingCandidates)
		
		while True:
			self.infoLog()
			self.infoLog('== COUNT {}', count)
			
			roundResult = self.countUntilExclude(remainingCandidates, elected)
			self.tally_history.append(roundResult.tally)
			
			# Process round
			
			self.exhausted += roundResult.exhausted
			for candidate in roundResult.provisionallyElected:
				elected.append(candidate)
			
			for candidate in roundResult.excluded:
				remainingCandidates.remove(candidate)
			for candidate in roundResult.excluded:
				for ballot in candidate.ballots:
					transferTo = self.surplusTransfer(ballot.ballot.preferences, candidate, elected, remainingCandidates)
					if transferTo == False:
						self.verboseLog('   - Exhausted {} votes via {}', self.toNum(ballot.value), ballot.ballot.prettyPreferences)
						self.exhausted += ballot.value
					else:
						self.verboseLog('   - Transferring {} votes to {} via {}', self.toNum(ballot.value), transferTo.name, ballot.ballot.prettyPreferences)
						transferTo.ctvv += ballot.value
						transferTo.ballots.append(ballot)
			
			if not self.args.get('fast', False) and roundResult.excluded:
				self.printVotes(remainingCandidates, elected)
			
			# Are we done yet?
			
			if self.args.get('fast', False) and len(remainingCandidates) <= self.args['seats']:
				remainingCandidates.sort(key=lambda k: k.ctvv, reverse=True)
				for candidate in remainingCandidates:
					if candidate not in elected:
						self.infoLog('**** {} provisionally elected on {} votes', candidate.name, self.toNum(candidate.ctvv))
						elected.append(candidate)
				return elected, None, self.exhausted
			
			if len(elected) >= self.args['seats']:
				return elected, None, self.exhausted
			
			count += 1
	
	@classmethod
	def getParser(cls):
		import argparse
		
		parser = argparse.ArgumentParser(description='Count an election using STV.', conflict_handler='resolve')
		parser.add_argument('--election', required=True, help='OpenSTV blt file')
		parser.add_argument('--verbose', help='Display extra information', action='store_true')
		parser.add_argument('--quiet', help='Silence all output except the bare minimum', action='store_true')
		parser.add_argument('--fast', help="Don't perform a full tally", action='store_true')
		parser.add_argument('--nums', help='Kind of arithmetic to use', choices=['float', 'fraction', 'decimal'], default='fraction')
		parser.add_argument('--noround', help="Display raw fractions instead of rounded decimals", action='store_true')
		parser.add_argument('--quota', help='The quota/threshold condition: >=Droop, >Hagenbach-Bischoff, etc.', choices=['geq-droop', 'gt-hb', 'geq-hb'], default='geq-droop')
		parser.add_argument('--quota-prog', help='Use a progressively-reducing quota', action='store_true')
		parser.add_argument('--ties', help='How to break ties, in preference order', choices=['manual', 'backward', 'random', 'all'], nargs='+', default=['manual'])
		parser.add_argument('--randfile', help='random.org signed JSON data')
		parser.add_argument('--randbyte', help='Index of byte in random data to start at', default='0')
		parser.add_argument('--countback', help="Store electing quota of votes for a given candidate ID and store in a given blt file", nargs=2)
		
		return parser
	
	@classmethod
	def main(cls):
		print('=== pyRCV {} ==='.format(version.VERSION))
		print()
		
		parser = cls.getParser()
		args = parser.parse_args()
		
		if args.nums == 'float':
			utils._numclass = float
		elif args.nums == 'decimal':
			import decimal
			utils._numclass = decimal.Decimal
		
		from .utils import blt
		
		# Read blt
		with open(args.election, 'r') as electionFile:
			electionLines = electionFile.read().splitlines()
			ballots, candidates, args.seats = blt.readBLT(electionLines)
		
		counter = cls(ballots, candidates, **vars(args))
		
		if args.verbose:
			for ballot in ballots:
				print("{} : {}".format(counter.toNum(ballot.value), ",".join([x.name for x in ballot.preferences])))
			print()
		
		elected, comments, exhausted = counter.countVotes()
		print()
		print("== TALLY COMPLETE")
		print()
		print("The winners are, in order of election:")
		
		print()
		for i, candidate in enumerate(elected):
			print("     {}{}".format(candidate.name, ' ({})'.format(comments[i]) if comments and comments[i] else ''))
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
			for peCandidate in elected:
				candidatesToExclude.append(peCandidate)
			
			with open(args.countback[1], 'w') as countbackFile:
				# use --noround to determine whether to use standard BLT format or rational BLT format
				stringify = str if args.noround else float
				
				
				
				print('\n'.join(utils.blt.writeBLT([common.Ballot(preferences=x.ballot.preferences, value=x.value, prettyPreferences=x.ballot.prettyPreferences) for x in candidate.ballots], candidates, 1, '', candidatesToExclude, stringify)), file=countbackFile)
		
		print()
		print("=== Tally computed by pyRCV {} ===".format(version.VERSION))

if __name__ == '__main__':
	STVCounter.main()
