""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2024 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
Therapy Models
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from neomodel import StructuredNode, StringProperty, FloatProperty, ArrayProperty, IntegerProperty, Relationship

class Therapy(StructuredNode):
    name = StringProperty(max_length=128)
    type = StringProperty(max_length=128)
    date = FloatProperty()

    def purge(self):
        self.delete()

class Medication(Therapy):
    medication = StringProperty()
    dosage = FloatProperty()
    frequency = StringProperty()

class ElectricalTherapy(Therapy):
    group_name = StringProperty()
    stimulation_type = StringProperty()
    device = StringProperty()
    
    settings = Relationship("ElectricalStimulation", "HAS_ELECTRICAL_STIMULATION")

    def purge(self):
        for setting in self.settings:
            setting.purge()
        self.delete()

class AdaptiveTherapy(ElectricalTherapy):
    pass

class ElectricalStimulation(StructuredNode):
    electrode = Relationship(".Device.Electrode", "USE_ELECTRODE")
    contact = ArrayProperty(IntegerProperty())
    return_contact = ArrayProperty(IntegerProperty())
    amplitude = ArrayProperty(FloatProperty())
    amplitude_unit = StringProperty()
    pulsewidth = FloatProperty()
    pulsewidth_unit = StringProperty()
    frequency = FloatProperty()
    cycling = FloatProperty()
    cycling_period = FloatProperty()

    waveform = StringProperty() # This needs to be implemented as a method later, typical options being passive or active, cathode/anode etc.

    def purge(self):
        self.delete()