# Copyright (C) 2019 Simon Biggs

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from pymedphys._base.delivery import DeliveryBase

from ..mudensity import calc_mu_density


class DeliveryMuDensity(DeliveryBase):
    def mudensity(
        self,
        gantry_angles=None,
        gantry_tolerance=3,
        grid_resolution=1,
        output_always_list=False,
    ):
        if gantry_angles is None:
            gantry_angles = 0
            gantry_tolerance = 500

        masked_by_gantry = self._mask_by_gantry(gantry_angles, gantry_tolerance)

        mudensities = []
        for delivery_data in masked_by_gantry:
            mudensities.append(
                calc_mu_density(
                    delivery_data.monitor_units,
                    delivery_data.mlc,
                    delivery_data.jaw,
                    grid_resolution=grid_resolution,
                )
            )

        if not output_always_list:
            if len(mudensities) == 1:
                return mudensities[0]

        return mudensities
