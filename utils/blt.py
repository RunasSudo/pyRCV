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

from .common import Ballot, Candidate

import sys

def readBLT(electionLines):
	ballotData = [] # Can't process until we know the candidates
	candidates = []
	
	# Read first line
	numCandidates = int(electionLines[0].split(' ')[0])
	seats = int(electionLines[0].split(' ')[1])
	
	# Read withdrawn candidates
	withdrawn = []
	i = 1
	if electionLines[i].startswith("-"):
		withdrawn = [int(x.lstrip("-")) - 1 for x in electionLines[i].split(" ")]
		i += 1
	
	# Read ballots
	for j in range(i, len(electionLines)):
		if electionLines[j] == '0': # End of ballots
			break
		bits = electionLines[j].split(' ')
		preferences = [int(x) - 1 for x in bits[1:] if x != '0']
		ballotData.append((bits[0], preferences))
	
	# Read candidates
	for k in range(j + 1, len(electionLines) - 1): # j + 1 to skip '0' line, len - 1 to skip title
		candidates.append(Candidate(electionLines[k].strip('"')))
	
	assert len(candidates) == numCandidates
	
	# Process ballots
	ballots = []
	for ballot in ballotData:
		preferences = [candidates[x] for x in ballot[1] if x not in withdrawn]
		ballots.append(Ballot(preferences, [x.name for x in preferences], ballot[0]))
	
	# Process withdrawn candidates
	withdrawnCandidates = [candidates[x] for x in withdrawn]
	for candidate in withdrawnCandidates:
		candidates.remove(candidate)
	
	return ballots, candidates, seats

def writeBLT(ballots, candidates, seats, name='', withdrawn=[], stringify=str):
	electionLines = []
	
	electionLines.append("{} {}".format(len(candidates), seats))
	
	if len(withdrawn) > 0:
		electionLines.append(" ".join(["-{}".format(candidates.index(candidate) + 1) for candidate in withdrawn]))
	
	for ballot in ballots:
		if ballot.preferences:
			electionLines.append("{} {} 0".format(stringify(ballot.value), " ".join(str(candidates.index(x) + 1) for x in ballot.preferences)))
		else:
			electionLines.append("{} 0".format(stringify(ballot.value)))
	
	electionLines.append("0")
	
	for candidate in candidates:
		electionLines.append('"{}"'.format(candidate.name))
	
	electionLines.append('"{}"'.format(name))
	
	return electionLines
