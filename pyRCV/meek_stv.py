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
	def countDistributeSurpluses(self, remainingCandidates, provisionallyElected, quota, roundProvisionallyElected):
		mostVotesElected = sorted(roundProvisionallyElected, key=lambda k: k.ctvv, reverse=True)
		self.infoLog('---- Distributing surpluses')
		# While surpluses remain
		while mostVotesElected and any(abs(c.ctvv - quota) > utils.num('0.00001') for c in mostVotesElected):
			# Recalculate weights
			for candidate in mostVotesElected:
				self.verboseLog('     Reducing {} keep value from {} to {}', candidate.name, self.toNum(candidate.keep_value), self.toNum(candidate.keep_value * quota / candidate.ctvv))
				candidate.keep_value *= quota / candidate.ctvv
			
			# Redistribute votes
			#for candidate in remainingCandidates:
			#	candidate.ctvv = utils.num('0')
			#	candidate.ballots.clear()
			self.resetCount(remainingCandidates)
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
		
		return roundProvisionallyElected
	
	def countVotes(self):
		self.totalBallots = self.totalVoteBallots(self.ballots)
		
		count = 1
		remainingCandidates = self.candidates[:]
		provisionallyElected = []
		
		while True:
			self.infoLog()
			self.infoLog("== COUNT {}".format(count))
			
			self.resetCount(remainingCandidates)
			self.exhausted = self.distributePreferences(self.ballots, remainingCandidates)
			
			roundResult = self.countUntilExclude(remainingCandidates, provisionallyElected)
			
			# Process round
			
			self.exhausted += roundResult.exhausted
			
			if roundResult.excluded:
				# Reset and reiterate
				for candidate in roundResult.excluded:
					candidate.keep_value = utils.num('0')
					remainingCandidates.remove(candidate)
				
				if self.args['fast'] and len(remainingCandidates) <= self.args['seats']:
					remainingCandidates.sort(key=lambda k: k.ctvv, reverse=True)
					for candidate in remainingCandidates:
						if candidate not in provisionallyElected:
							print("**** {} provisionally elected on {} votes".format(candidate.name, self.toNum(candidate.ctvv)))
							provisionallyElected.append(candidate)
					return provisionallyElected, self.exhausted
				
				count += 1
				
				if len(roundResult.provisionallyElected) == len(remainingCandidates) and len(roundResult.provisionallyElected) == self.args['seats']:
					# Meek STV goes funny if we continue to count aftering excluding the last non-winner
					pass
				else:
					continue
			
			# We must be done!
			
			for candidate in roundResult.provisionallyElected:
				provisionallyElected.append(candidate)
			
			# Sort by order of election via keep value
			provisionallyElected.sort(key=lambda candidate: candidate.keep_value)
			
			return provisionallyElected, [self.toNum(candidate.keep_value) for candidate in provisionallyElected], self.exhausted

if __name__ == '__main__':
	MeekSTVCounter.main()
