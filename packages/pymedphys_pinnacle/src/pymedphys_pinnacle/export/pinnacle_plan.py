# Copyright (C) 2019 South Western Sydney Local Health District,
# University of New South Wales

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version (the "AGPL-3.0+").

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License and the additional terms for more
# details.

# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# ADDITIONAL TERMS are also included as allowed by Section 7 of the GNU
# Affero General Public License. These additional terms are Sections 1, 5,
# 6, 7, 8, and 9 from the Apache License, Version 2.0 (the "Apache-2.0")
# where all references to the definition "License" are instead defined to
# mean the AGPL-3.0+.

# You should have received a copy of the Apache-2.0 along with this
# program. If not, see <http://www.apache.org/licenses/LICENSE-2.0>.

# This work is derived from:
# https://github.com/AndrewWAlexander/Pinnacle-tar-DICOM
# which is released under the following license:

# Copyright (c) [2017] [Colleen Henschel, Andrew Alexander]

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import re

import pydicom

from .pinn_yaml import pinn_to_dict
from .rtstruct import find_iso_center


# Medical Connections offers free valid UIDs
# (http://www.medicalconnections.co.uk/FreeUID.html)
# Their service was used to obtain the following root UID for this tool:
UID_PREFIX = "1.2.826.0.1.3680043.10.202."

# This class holds all information relating to the Pinnacle Plan


class PinnaclePlan:

    def __init__(self, pinnacle, path, plan):
        self._pinnacle = pinnacle
        self._path = path
        self._plan_info = plan

        self._machine_info = None  # Data of the machines used for this plan
        self._trials = None  # Data found in plan.Trial
        self._trial_info = None  # 'Active' trial for this plan
        self._points = None  # Data found in plan.Points
        self._patient_setup = None  # Data found in PatientSetup file
        self._primary_image = None  # Primary image for this plan
        self._uid_prefix = UID_PREFIX  # The prefix for UIDs generated

        self._roi_count = 0  # Store the total number of ROIs
        self._iso_center = []  # Store the iso center of this plan
        self._ct_center = []  # Store the ct center of the primary image of this plan
        self._dose_ref_pt = []  # Store the dose ref point of this plan

        self._plan_inst_uid = None  # UID for RTPlan instance
        self._dose_inst_uid = None  # UID for RTDose instance
        self._struct_inst_uid = None  # UID for RTStruct instance

        for image in pinnacle.images:
            if image.image['ImageSetID'] == self.plan_info["PrimaryCTImageSetID"]:
                self.primary_image = image

    @property
    def logger(self):
        return self._pinnacle.logger

    @property
    def pinnacle(self):
        return self._pinnacle

    @property
    def path(self):
        return self._path

    @property
    def machine_info(self):

        if not self._machine_info:
            path_machine = os.path.join(self._path, "plan.Pinnacle.Machines")
            self.logger.debug('Reading machine data from: ' + path_machine)
            self._machine_info = pinn_to_dict(path_machine)

        return self._machine_info

    @property
    def trials(self):

        if not self._trials:
            path_trial = os.path.join(self._path, "plan.Trial")
            self.logger.debug('Reading trial data from: ' + path_trial)
            self._trials = pinn_to_dict(path_trial)
            if isinstance(self._trials, dict):
                self._trials = [self._trials['Trial']]

            # Select trial with FINAL in name as active trial for this plan
            # If no FINAL trial found then select first trial
            for trial in self._trials:
                if 'FINAL' in trial['Name'].upper():
                    self._trial_info = trial
                    break

            if not self._trial_info:
                self._trial_info = self._trials[0]

            self.logger.debug('Number of trials read: ' +
                              str(len(self._trials)))
            self.logger.debug('Active Trial: ' + self._trial_info['Name'])

        return self._trials

    @property
    def active_trial(self):
        return self._trial_info

    @active_trial.setter
    def active_trial(self, trial_name):

        if isinstance(trial_name, str):
            for trial in self._trials:
                if trial['Name'] == trial_name:
                    self._trial_info = trial
                    self.logger.info('Active Trial set: ' + trial_name)
                    return True

        return False

    @property
    def plan_info(self):
        return self._plan_info

    @property
    def trial_info(self):

        if not self._trial_info:
            self.trials

        return self._trial_info

    @property
    def points(self):

        if not self._points:
            path_points = os.path.join(self._path, "plan.Points")
            self.logger.debug('Reading points data from: ' + path_points)
            self._points = pinn_to_dict(path_points)

            if type(self._points) == dict:
                self._points = [self._points['Poi']]

            if self._points == None:
                self._points = []

        return self._points

    @property
    def patient_position(self):

        if not self._patient_setup:
            self._patient_setup = pinn_to_dict(
                os.path.join(self._path, "plan.PatientSetup"))

        pat_pos = ""

        if "Head First" in self._patient_setup["Orientation"]:
            pat_pos = "HF"
        elif "Feet First" in self._patient_setup["Orientation"]:
            pat_pos = "FF"

        if "supine" in self._patient_setup["Position"]:
            pat_pos = pat_pos + "S"
        elif "prone" in self._patient_setup["Position"]:
            pat_pos = pat_pos + "P"
        elif "decubitus right" in self._patient_setup["Position"] or "Decuibitus Right" in self._patient_setup["Position"]:
            pat_pos = pat_pos + "DR"
        elif "decubitus left" in self._patient_setup["Position"] or "Decuibitus Left" in self._patient_setup["Position"]:
            pat_pos = pat_pos + "DL"

        return pat_pos

    @property
    def iso_center(self):
        # If the iso center hasn't been set, then call read points function from
        # RTStruct which sets the iso center

        if len(self._iso_center) == 0:
            find_iso_center(self)

        return self._iso_center

    @iso_center.setter
    def iso_center(self, iso_center):
        self._iso_center = iso_center

    def is_prefix_valid(self, prefix):

        if re.match(pydicom.uid.RE_VALID_UID_PREFIX, prefix):
            return True

        return False

    def generate_uids(self, uid_type='HASH'):
        # If uid_type HASH is supplied then entropy will be generated
        # to hash to consistant UIDs. If not then random UIDs will be
        # generated.

        entropy_srcs = None
        if uid_type == 'HASH':
            entropy_srcs = []
            entropy_srcs.append(self._pinnacle.patient_info[
                                'MedicalRecordNumber'])
            entropy_srcs.append(self.plan_info['PlanName'])
            entropy_srcs.append(self.trial_info['Name'])
            entropy_srcs.append(self.trial_info[
                                'ObjectVersion']['WriteTimeStamp'])

        RTPLAN_prefix = self._uid_prefix + "1."
        self._plan_inst_uid = pydicom.uid.generate_uid(
            prefix=RTPLAN_prefix, entropy_srcs=entropy_srcs)
        RTDOSE_prefix = self._uid_prefix + "2."
        self._dose_inst_uid = pydicom.uid.generate_uid(
            prefix=RTDOSE_prefix, entropy_srcs=entropy_srcs)
        RTSTRUCT_prefix = self._uid_prefix + "3."
        self._struct_inst_uid = pydicom.uid.generate_uid(
            prefix=RTSTRUCT_prefix, entropy_srcs=entropy_srcs)

        self.logger.debug('Plan Instance UID: ' + self._plan_inst_uid)
        self.logger.debug('Dose Instance UID: ' + self._dose_inst_uid)
        self.logger.debug('Struct Instance UID: ' + self._struct_inst_uid)

    @property
    def plan_inst_uid(self):

        if not self._plan_inst_uid:
            self.generate_uids()

        return self._plan_inst_uid

    @property
    def dose_inst_uid(self):

        if not self._dose_inst_uid:
            self.generate_uids()

        return self._dose_inst_uid

    @property
    def struct_inst_uid(self):

        if not self._struct_inst_uid:
            self.generate_uids()

        return self._struct_inst_uid

    # Convert the point from the pinnacle plan format to dicom
    def convert_point(self, point):

        image_header = self.primary_image.image_header

        refpoint = [point['XCoord']*10, point['YCoord']*10, point['ZCoord']*10]
        if image_header["patient_position"] == 'HFP' or image_header["patient_position"] == 'FFS':
            refpoint[0] = -refpoint[0]
        if image_header["patient_position"] == 'HFS' or image_header["patient_position"] == 'FFS':
            refpoint[1] = -(refpoint[1])
        if image_header["patient_position"] == 'HFS' or image_header["patient_position"] == 'HFP':
            refpoint[2] = -(refpoint[2])

        point['refpoint'] = refpoint

        refpoint[0] = round(refpoint[0], 5)
        refpoint[1] = round(refpoint[1], 5)
        refpoint[2] = round(refpoint[2], 5)

        return refpoint