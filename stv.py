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

import copy
import itertools
from fractions import Fraction

# Represents the outcome of the current round
class STVResult:
	def __init__(self, excluded=[], provisionallyElected=[], exhausted=0):
		self.excluded = excluded
		self.provisionallyElected = provisionallyElected
		self.exhausted = exhausted

class STVCounter:
	def __init__(self, ballots, candidates, **kwargs):
		self.args = kwargs
		
		self.ballots = ballots
		self.candidates = candidates
		
		self.exhausted = 0
		
		self.numclass = Fraction
	
	def verboseLog(self, string):
		if self.args['verbose']:
			print(string)
	
	def resetCount(self, ballots, candidates):
		for ballot in ballots:
			ballot.value = ballot.origValue
		for candidate in candidates:
			candidate.ctvv = self.numclass('0')
			candidate.ballots.clear()
	
	def distributePreferences(self, ballots, remainingCandidates):
		exhausted = self.numclass('0')
		
		for ballot in ballots:
			isExhausted = True
			for preference in ballot.preferences:
				if preference in remainingCandidates:
					self.verboseLog("   - Assigning {} votes to {} via {}".format(self.toNum(ballot.value), preference.name, ballot.prettyPreferences))
					
					isExhausted = False
					preference.ctvv += ballot.value
					preference.ballots.append(ballot)
					
					break
			if isExhausted:
				self.verboseLog("   - Exhausted {} votes via {}".format(self.toNum(ballot.value), ballot.prettyPreferences))
				exhausted += ballot.value
				ballot.value = self.numclass('0')
		
		return exhausted
	
	def toNum(self, num):
		if self.args['noround']:
			return str(num)
		else:
			return "{:.2f}".format(float(num))
	
	def totalVoteBallots(self, ballots):
		tv = self.numclass('0')
		for ballot in ballots:
			tv += ballot.value
		return tv
	
	def totalVote(self, candidates):
		tv = self.numclass('0')
		for candidate in candidates:
			tv += candidate.ctvv
		return tv
	
	def calcQuotaNum(self, totalVote, numSeats):
		if '-hb' in self.args['quota']:
			return totalVote / (numSeats + 1)
		if '-droop' in self.args['quota']:
			return self.numclass((totalVote / (numSeats + 1) + 1).__floor__())
	
	def calcQuota(self, remainingCandidates):
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
		print()
		for candidate in remainingCandidates:
			print("    {}{}: {}".format("*" if candidate in provisionallyElected else " ", candidate.name, self.toNum(candidate.ctvv)))
		print()
	
	def countUntilExclude(self, remainingCandidates, provisionallyElected):
		roundProvisionallyElected = []
		roundExhausted = self.numclass('0')
		
		self.printVotes(remainingCandidates, provisionallyElected)
		
		quota = self.calcQuota(remainingCandidates)
		
		print("---- Total Votes: {}".format(self.toNum(self.totalBallots)))
		print("----   Of which not exhausted: {}".format(self.toNum(self.totalVote(remainingCandidates))))
		print("----   Of which exhausted: {}".format(self.toNum(self.exhausted + roundExhausted)))
		print("---- Quota: {}".format(self.toNum(quota)))
		print()
		
		remainingCandidates.sort(key=lambda k: k.ctvv, reverse=True)
		for candidate in remainingCandidates:
			if candidate not in (provisionallyElected + roundProvisionallyElected) and self.hasQuota(candidate, quota):
				print("**** {} provisionally elected".format(candidate.name))
				roundProvisionallyElected.append(candidate)
		
		if self.args['fast'] and (len(provisionallyElected) + len(roundProvisionallyElected)) >= self.args['seats']:
			return STVResult([], roundProvisionallyElected, roundExhausted)
		
		mostVotesElected = sorted(roundProvisionallyElected, key=lambda k: k.ctvv, reverse=True)
		# While surpluses remain
		while mostVotesElected and mostVotesElected[0].ctvv > quota:
			for candidate in mostVotesElected:
				if candidate.ctvv > quota:
					multiplier = (candidate.ctvv - quota) / candidate.ctvv
					print("---- Transferring surplus from {} at value {}".format(candidate.name, self.toNum(multiplier)))
					
					for ballot in candidate.ballots:
						transferTo = self.surplusTransfer(ballot.preferences, candidate, provisionallyElected + roundProvisionallyElected, remainingCandidates)
						if transferTo == False:
							self.verboseLog("   - Exhausted {} votes via {}".format(self.toNum(ballot.value), ballot.prettyPreferences))
							ballot.value *= (1 - multiplier)
							# roundExhausted += ballot.value * multiplier
							# Since it retains its value and remains in the count, we will not count it as exhausted.
						else:
							self.verboseLog("   - Transferring {} votes to {} via {}".format(self.toNum(ballot.value), transferTo.name, ballot.prettyPreferences))
							newBallot = copy.copy(ballot)
							ballot.value *= (1 - multiplier)
							newBallot.value *= multiplier
							transferTo.ctvv += newBallot.value
							transferTo.ballots.append(newBallot)
					
					candidate.ctvv = quota
					
					self.printVotes(remainingCandidates, provisionallyElected + roundProvisionallyElected)
					
					for candidate in remainingCandidates:
						if candidate not in (provisionallyElected + roundProvisionallyElected) and self.hasQuota(candidate, quota):
							print("**** {} provisionally elected".format(candidate.name))
							roundProvisionallyElected.append(candidate)
					
					if self.args['fast'] and (len(provisionallyElected) + len(roundProvisionallyElected)) >= self.args['seats']:
						return STVResult([], roundProvisionallyElected, roundExhausted)
			mostVotesElected = sorted(roundProvisionallyElected, key=lambda k: k.ctvv, reverse=True)
		
		# We only want to do this after preferences have been distributed
		if not self.args['fast'] and len(remainingCandidates) <= self.args['seats']:
			remainingCandidates.sort(key=lambda k: k.ctvv, reverse=True)
			for candidate in remainingCandidates:
				if candidate not in (provisionallyElected + roundProvisionallyElected):
					print("**** {} provisionally elected on {} quotas".format(candidate.name, self.toNum(candidate.ctvv / quota)))
					roundProvisionallyElected.append(candidate)
			return STVResult([], roundProvisionallyElected, roundExhausted)
		
		# Bulk exclude as many candidates as possible
		remainingCandidates.sort(key=lambda k: k.ctvv)
		grouped = [(x, list(y)) for x, y in itertools.groupby([x for x in remainingCandidates if x not in (provisionallyElected + roundProvisionallyElected)], lambda k: k.ctvv)] # ily python
		
		votesToExclude = self.numclass('0')
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
				print("---- Bulk excluding {}".format(candidate.name))
			return STVResult(candidatesToExclude, roundProvisionallyElected, roundExhausted)
		else:
			# Just exclude one candidate then
			# Check for a tie
			toExclude = 0
			if len(remainingCandidates) > 1 and remainingCandidates[0].ctvv == remainingCandidates[1].ctvv:
				print("---- There is a tie for last place:")
				for i in range(0, len(remainingCandidates)):
					if remainingCandidates[i].ctvv == remainingCandidates[0].ctvv:
						print("     {}. {}".format(i, remainingCandidates[i].name))
				print("---- Which candidate to exclude?")
				toExclude = int(input())
			
			print("---- Excluding {}".format(remainingCandidates[toExclude].name))
			return STVResult([remainingCandidates[toExclude]], roundProvisionallyElected, roundExhausted)
	
	def countVotes(self):
		self.totalBallots = self.totalVoteBallots(self.ballots)
		
		count = 1
		remainingCandidates = self.candidates[:]
		elected = []
		
		self.resetCount(self.ballots, remainingCandidates)
		self.exhausted = self.distributePreferences(self.ballots, remainingCandidates)
		
		while True:
			print()
			print("== COUNT {}".format(count))
			
			roundResult = self.countUntilExclude(remainingCandidates, elected)
			
			# Process round
			
			self.exhausted += roundResult.exhausted
			for candidate in roundResult.provisionallyElected:
				elected.append(candidate)
			
			for candidate in roundResult.excluded:
				remainingCandidates.remove(candidate)
			for candidate in roundResult.excluded:
				for ballot in candidate.ballots:
					transferTo = self.surplusTransfer(ballot.preferences, candidate, elected, remainingCandidates)
					if transferTo == False:
						self.verboseLog("   - Exhausted {} votes via {}".format(self.toNum(ballot.value), ballot.prettyPreferences))
						self.exhausted += ballot.value
					else:
						self.verboseLog("   - Transferring {} votes to {} via {}".format(self.toNum(ballot.value), transferTo.name, ballot.prettyPreferences))
						transferTo.ctvv += ballot.value
						transferTo.ballots.append(ballot)
			
			# Are we done yet?
			
			if self.args['fast'] and len(remainingCandidates) <= self.args['seats']:
				remainingCandidates.sort(key=lambda k: k.ctvv, reverse=True)
				for candidate in remainingCandidates:
					if candidate not in elected:
						print("**** {} provisionally elected on {} votes".format(candidate.name, self.toNum(candidate.ctvv)))
						elected.append(candidate)
				return elected, self.exhausted
			
			if len(elected) >= self.args['seats']:
				return elected, self.exhausted
			
			count += 1
	
	@classmethod
	def getParser(cls):
		import argparse
		
		parser = argparse.ArgumentParser(description='Count an election using STV.', conflict_handler='resolve')
		parser.add_argument('election', help='OpenSTV blt file')
		parser.add_argument('--verbose', help='Display extra information', action='store_true')
		parser.add_argument('--fast', help="Don't perform a full tally", action='store_true')
		parser.add_argument('--noround', help="Display raw fractions instead of rounded decimals", action='store_true')
		parser.add_argument('--quota', help='The quota/threshold condition: >=Droop or >Hagenbach-Bischoff', choices=['geq-droop', 'gt-hb'], default='geq-droop')
		parser.add_argument('--countback', help="Store electing quota of votes for a given candidate ID and store in a given blt file", nargs=2)
		
		return parser
	
	@classmethod
	def main(cls):
		import utils.blt
		
		parser = cls.getParser()
		args = parser.parse_args()
		
		# Read blt
		with open(args.election, 'r') as electionFile:
			electionLines = electionFile.read().splitlines()
			ballots, candidates, args.seats = utils.blt.readBLT(electionLines)
		
		counter = cls(ballots, candidates, **vars(args))
		
		if args.verbose:
			for ballot in ballots:
				print("{} : {}".format(counter.toNum(ballot.value), ",".join([x.name for x in ballot.preferences])))
		
		elected, exhausted = counter.countVotes()
		print()
		print("== TALLY COMPLETE")
		print()
		print("The winners are, in order of election:")
		
		print()
		for candidate in elected:
			print("     {}".format(candidate.name))
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
				utils.blt.writeBLT(candidate.ballots, candidates, 1, candidatesToExclude, countbackFile, stringify)

if __name__ == '__main__':
	STVCounter.main()
