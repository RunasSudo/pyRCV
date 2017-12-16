# -*- coding: utf-8 -*-
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

from . import numclass

class Ballot:
	def __init__(self, preferences, prettyPreferences, value=1):
		self.preferences = preferences
		self.prettyPreferences = prettyPreferences
		
		self.value = self.origValue = numclass(value)
	
	def copy(self):
		copy = Ballot(self.preferences, self.prettyPreferences, self.origValue)
		copy.value = self.value
		return copy

class Candidate:
	def __init__(self, name):
		self.name = name
		self.ctvv = numclass('0')
		self.ballots = []
	
	def __repr__(self):
		return '<{}: {}>'.format(self.__class__.__name__, self.name)
