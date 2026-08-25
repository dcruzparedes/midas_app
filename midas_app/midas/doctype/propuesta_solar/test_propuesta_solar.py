# Copyright (c) 2026, MIDAS and Contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase


class TestPropuestaSolar(FrappeTestCase):
	def test_calculate_basic_proposal(self):
		proposal = frappe.new_doc("Propuesta Solar")
		proposal.project_department = "Cortés"
		proposal.tariff_type = "Media Tensión"
		proposal.monthly_consumption = 15000
		proposal.desired_savings = 40
		proposal.panel_power = 630
		proposal.panel_size = 2.623
		proposal.panel_price = 0.75

		proposal.calculate()

		self.assertAlmostEqual(proposal.dc_power, 52.17391304347826, places=2)
		self.assertAlmostEqual(proposal.ac_power, 41.73913043478261, places=2)
		self.assertAlmostEqual(proposal.energy_generated, 72000.0, places=0)
		self.assertAlmostEqual(proposal.investment_cost, 39130.434782608696, places=0)
		self.assertAlmostEqual(proposal.payback_period, 2.535, places=2)
