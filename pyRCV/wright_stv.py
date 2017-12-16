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

class WrightSTVCounter(stv.STVCounter):
	def calcQuota(self, remainingCandidates):
		return self.calcQuotaNum(self.totalVote(remainingCandidates), self.args['seats'])
	
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

if __name__ == '__main__':
	WrightSTVCounter.main()
