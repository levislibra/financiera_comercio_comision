# -*- coding: utf-8 -*-

from openerp import models, fields, api

class financiera_comercio_comision(models.Model):
	_name = 'financiera.comercio.comision'

	name = fields.Char('Nombre')
	comercio_id = fields.Many2one('financiera.entidad', 'Comercio', domain="[('type', '=', 'comercio')]")
	sobre = fields.Selection([('prestamo', 'Prestamo'), ('cuota', 'Cuota')], string='Aplica sobre', default='prestamo')
	comision_prestamo = fields.Selection([('monto_solicitado', 'Monto Solicitado'), ('monto_fijo', 'Monto Fijo')], string='Opciones')
	comision_cuota = fields.Selection([('monto_cuota', 'Monto Cuota'), ('monto_fijo', 'Monto Fijo')], string='Opciones')
	tasa = fields.Float('Tasa a aplicar', digits=(16,4))
	monto = fields.Float('Monto a aplicar', digits=(16,2))
	activo = fields.Boolean("Estado", default=False)

	@api.one
	@api.onchange('sobre')
	def onchange_sobre(self):
		self.comision_prestamo = None
		self.comision_cuota = None
		self.tasa = 0
		self.monto = 0

class ExtendsFinancieraSucursal(models.Model):
	_inherit = 'financiera.entidad' 
	_name = 'financiera.entidad'

	partner_id = fields.Many2one('res.partner', 'Proveedor')