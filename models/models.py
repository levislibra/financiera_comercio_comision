# -*- coding: utf-8 -*-

from openerp import models, fields, api
from datetime import datetime, timedelta

class FinancieraComision(models.Model):
	_name = 'financiera.comision'

	name = fields.Char('Nombre')
	# active = fields.Boolean("Activa", default=True)
	state = fields.Selection([('borrador', 'Borrador'), ('confirmada', 'Confirmada'), ('obsoleta', 'Obsoleta')], string='Estado', readonly=True, default='borrador')
	comision_global = fields.Boolean('Comision global', default=True)
	entidad_id = fields.Many2one('financiera.entidad', 'Entidad')
	start_date = fields.Date('Fecha desde')
	end_date = fields.Date('Fecha hasta')
	sobre = fields.Selection([('prestamo', 'Prestamo'), ('cuota', 'Cuota')], string='Aplica sobre', default='prestamo')
	comision_prestamo = fields.Selection([('monto_solicitado', 'Tasa sobre Monto Solicitado'), ('monto_fijo', 'Monto Fijo')], string='Opciones sobre Prestamo')
	comision_cuota = fields.Selection([('monto_cuota', 'Tasa sobre Monto de la Cuota'), ('monto_fijo', 'Monto Fijo')], string='Opciones sobre Cuota')
	tasa = fields.Float('Tasa a aplicar', digits=(16,4))
	monto = fields.Float('Monto a aplicar', digits=(16,2))
	journal_ids = fields.Many2many('account.journal', 'financiera_comision_journal_rel', 'comision_id', 'journal_id', string='Metodo de Pago/Cobro', domain="[('type', 'in', ('cash', 'bank'))]")
	partner_id = fields.Many2one('res.partner', 'Facturara', domain="[('supplier', '=', True)]")
	account_payment_term_id = fields.Many2one('account.payment.term', 'Plazo de pago')
	iva = fields.Boolean('Calcular IVA')
	iva_incluido = fields.Boolean('IVA incluido')
	vat_tax_id = fields.Many2one('account.tax', 'Tasa de IVA', domain="[('type_tax_use', '=', 'purchase')]")
	journal_id = fields.Many2one('account.journal', 'Diario', domain="[('type', '=', 'purchase')]")
	detalle_factura = fields.Char('Detalle en linea de factura')
	company_id = fields.Many2one('res.company', 'Empresa', required=False, default=lambda self: self.env['res.company']._company_default_get('financiera.comision'))

	@api.one
	@api.onchange('sobre')
	def _onchange_sobre(self):
		self.comision_prestamo = None
		self.comision_cuota = None
		self.tasa = 0
		self.monto = 0

	@api.one
	@api.onchange('entidad_id')
	def _onchange_entidad_id(self):
		if len(self.entidad_id) > 0 and len(self.entidad_id.partner_id) > 0:
			self.partner_id = self.entidad_id.partner_id.id

	@api.one
	@api.onchange('comision_global')
 	def _onchange_comision_global(self):
 		self.entidad_id = None

 	@api.one
 	@api.onchange('name')
 	def _onchange_name(self):
 		self.detalle_factura = self.name

	@api.one
	def confirmar_comision(self):
		self.state = 'confirmada'

	@api.one
	def depreciar_comision(self):
		self.state = 'obsoleta'

	@api.one
	def editar_comision(self):
		self.state = 'borrador'


class ExtendsFinancieraSucursal(models.Model):
	_inherit = 'financiera.entidad' 
	_name = 'financiera.entidad'

	partner_id = fields.Many2one('res.partner', 'Proveedor', domain="[('supplier', '=', True)]")

class ExtendsResPartner(models.Model):
	_inherit = 'res.partner' 
	_name = 'res.partner'

	@api.model
	def default_get(self, values):
		rec = super(ExtendsResPartner, self).default_get(values)
		context = dict(self._context or {})
		active_model = context.get('active_model')
		if active_model in ['financiera.grupo.comision', 'financiera.entidad']:
			rec.update({
				'supplier': True,
				'customer': False,
			})
		return rec


	@api.model
	def create(self, values):
		rec = super(ExtendsResPartner, self).create(values)
		context = dict(self._context or {})
		active_model = context.get('active_model')
		current_uid = context.get('uid')
		if active_model in ['financiera.grupo.comision', 'financiera.entidad']:
			rec.update({
				'supplier': True,
				'customer': False,
			})
		return rec

class ExtendsAccountInvoice(models.Model):
	_inherit = 'account.invoice' 
	_name = 'account.invoice'

	comision_prestamo_id = fields.Many2one('financiera.prestamo', 'Comision Prestamo')
	comision_cuota_id = fields.Many2one('financiera.prestamo.cuota', 'Comision Cuota')
	payment_comision_id = fields.Many2one('account.payment', 'Pago generador comision')

class ExtendsAccountPayment(models.Model):
	_inherit = 'account.payment'
	_name = 'account.payment'

	invoice_comisiones_ids = fields.One2many('account.invoice', 'payment_comision_id', 'Facturas de Comisiones')

	@api.multi
	def cancel(self):
		res = super(ExtendsAccountPayment, self).cancel()
		for invoice_id in self.invoice_comisiones_ids:
			invoice_id.signal_workflow('invoice_cancel')

class ExtendsFinancieraPrestamo(models.Model):
	_inherit = 'financiera.prestamo' 
	_name = 'financiera.prestamo'

	invoice_comisiones_ids = fields.One2many('account.invoice', 'comision_prestamo_id', 'Facturas de Comisiones')
	comisiones_ids = fields.Many2many('financiera.comision', 'financiera_prestamo_comision_rel', 'prestamo_id', 'comision_id', string='Comisiones que Aplican')

	def comisiones_prestamo(self):
		cr = self.env.cr
		uid = self.env.uid
		entidad_id = None
		if len(self.comercio_id) > 0:
			entidad_id = self.comercio_id.id
		else:
			entidad_id = self.sucursal_id.id
		journal_id = -1
		if len(self.payment_ids) > 0:
			indice_ultimo_pago = len(self.payment_ids)-1
			journal_id = self.payment_ids[indice_ultimo_pago].journal_id.id
		comisiones_obj = self.pool.get('financiera.comision')
		domain = [
			('sobre', '=', 'prestamo'),
			('state', '=', 'confirmada'),
			'|', ('comision_global', '=', True),('entidad_id', '=', entidad_id),
			'|', ('journal_ids', '=', False), ('journal_ids', 'in', [journal_id]),
			('start_date', '<=', self.fecha),
			'|', ('end_date', '=', False), ('end_date', '>=', self.fecha),
			('company_id', '=', self.company_id.id)]
		comisiones_ids = comisiones_obj.search(cr, uid, domain)
		for _id in comisiones_ids:
			self.comisiones_ids = [(4, _id)]
		return comisiones_ids


	@api.one
	def generar_comision(self, comision_id):
		vat_tax_id = None
		invoice_line_tax_ids = None
		price_unit = 0
		flag_facturar = True
		ail_ids = []

		if comision_id.iva and len(comision_id.vat_tax_id) > 0:
			vat_tax_id = comision_id.vat_tax_id.id
			invoice_line_tax_ids = [(6, 0, [vat_tax_id])]
		else:
			vat_tax_id = None
			invoice_line_tax_ids = None
		journal_id = comision_id.journal_id
		if comision_id.comision_prestamo == 'monto_solicitado':
			comision_tasa = comision_id.tasa / 100
			monto = 0
			if len(self.payment_ids) > 0:
				indice_ultimo_pago = len(self.payment_ids)-1
				monto = self.payment_ids[indice_ultimo_pago].amount
			price_unit = monto * comision_tasa
		elif comision_id.comision_prestamo == 'monto_fijo':
			price_unit = comision_id.monto
			if len(self.payment_ids) > 0:
				# Si Tenia otros pagos y existe una factura de comision
				# por el mismo monto a generar no sera considerada.
				for invoice_id in self.invoice_comisiones_ids:
					if invoice_id.state != 'cancel' and invoice_id.amount_total == price_unit:
						flag_facturar = False
		if comision_id.iva and comision_id.iva_incluido:
			price_unit = price_unit / (1+(comision_id.vat_tax_id.amount/100))
		if flag_facturar:
			# Create invoice line
			ail = {
				'name': comision_id.detalle_factura,
				'quantity':1,
				'price_unit': price_unit,
				# 'vat_tax_id': vat_tax_id,
				'invoice_line_tax_ids': invoice_line_tax_ids,
				'report_invoice_line_tax_ids': invoice_line_tax_ids,
				'account_id': journal_id.default_debit_account_id.id,
				'company_id': comision_id.company_id.id,
			}
			ail_ids.append((0,0,ail))

			account_invoice_supplier = {
				'description_financiera': comision_id.detalle_factura,
				'account_id': comision_id.partner_id.property_account_payable_id.id,
				'partner_id': comision_id.partner_id.id,
				'journal_id': journal_id.id,
				'currency_id': self.currency_id.id,
				'company_id': comision_id.company_id.id,
				'date': datetime.now(),
				'invoice_line_ids': ail_ids,
				'type': 'in_invoice',
				'payment_term_id': comision_id.account_payment_term_id.id,
			}
			new_invoice_id = self.env['account.invoice'].create(account_invoice_supplier)
			self.invoice_comisiones_ids = [new_invoice_id.id]
		return new_invoice_id

	@api.one
	def confirmar_pagar_prestamo(self, payment_date, payment_amount, payment_journal_id, payment_communication):
		rec = super(ExtendsFinancieraPrestamo, self).confirmar_pagar_prestamo(payment_date, payment_amount, payment_journal_id, payment_communication)
		comisiones_ids = self.comisiones_prestamo()
		for _id in comisiones_ids:
			comision_id = self.env['financiera.comision'].browse(_id)
			invoice_id = self.generar_comision(comision_id)
			self.payment_last_id.invoice_comisiones_ids = [invoice_id[0].id]


class ExtendsFinancieraPrestamoCuota(models.Model):
	_inherit = 'financiera.prestamo.cuota' 
	_name = 'financiera.prestamo.cuota'

	invoice_comisiones_ids = fields.One2many('account.invoice', 'comision_cuota_id', 'Facturas de Comisiones')
	comisiones_ids = fields.Many2many('financiera.comision', 'financiera_cuota_comision_rel', 'cuota_id', 'comision_id', string='Comisiones que Aplican')

	def comisiones_cuota(self):
		cr = self.env.cr
		uid = self.env.uid
		entidad_id = None
		if len(self.comercio_id) > 0:
			entidad_id = self.comercio_id.id
		else:
			entidad_id = self.sucursal_id.id
		journal_id = -1
		payment_date = None
		if len(self.payment_ids) > 0:
			indice_ultimo_pago = len(self.payment_ids)-1
			journal_id = self.payment_ids[indice_ultimo_pago].journal_id.id
			payment_date = self.payment_ids[indice_ultimo_pago].payment_date
		comisiones_obj = self.pool.get('financiera.comision')
		domain = [
			('sobre', '=', 'cuota'),
			('state', '=', 'confirmada'),
			'|', ('comision_global', '=', True),('entidad_id', '=', entidad_id),
			'|', ('journal_ids', '=', False), ('journal_ids', 'in', [journal_id]),
			('start_date', '<=', payment_date),
			'|', ('end_date', '=', False), ('end_date', '>=', payment_date),
			('company_id', '=', self.company_id.id)]
		comisiones_ids = comisiones_obj.search(cr, uid, domain)
		for _id in comisiones_ids:
			self.comisiones_ids = [(4, _id)]
		return comisiones_ids


	@api.one
	def generar_comision(self, comision_id):
		vat_tax_id = None
		invoice_line_tax_ids = None
		price_unit = 0
		flag_facturar = True
		ail_ids = []

		if comision_id.iva and len(comision_id.vat_tax_id) > 0:
			vat_tax_id = comision_id.vat_tax_id.id
			invoice_line_tax_ids = [(6, 0, [vat_tax_id])]
		else:
			vat_tax_id = None
			invoice_line_tax_ids = None
		journal_id = comision_id.journal_id
		if comision_id.comision_cuota == 'monto_cuota':
			comision_tasa = comision_id.tasa / 100
			monto = 0
			if len(self.payment_ids) > 0:
				indice_ultimo_pago = len(self.payment_ids)-1
				monto = self.payment_ids[indice_ultimo_pago].amount
			price_unit = monto * comision_tasa
		elif comision_id.comision_cuota == 'monto_fijo':
			price_unit = comision_id.monto
			if len(self.payment_ids) > 0:
				# Si Tenia otros pagos y existe una factura de comision
				# por el mismo monto a generar no sera considerada.
				for invoice_id in self.invoice_comisiones_ids:
					if invoice_id.state != 'cancel' and invoice_id.amount_total == price_unit:
						flag_facturar = False
		if comision_id.iva and comision_id.iva_incluido:
			price_unit = price_unit / (1+(comision_id.vat_tax_id.amount/100))
		if flag_facturar:
			# Create invoice line
			ail = {
				'name': comision_id.detalle_factura,
				'quantity':1,
				'price_unit': price_unit,
				# 'vat_tax_id': vat_tax_id,
				'invoice_line_tax_ids': invoice_line_tax_ids,
				'report_invoice_line_tax_ids': invoice_line_tax_ids,
				'account_id': journal_id.default_debit_account_id.id,
				'company_id': comision_id.company_id.id,
			}
			ail_ids.append((0,0,ail))

			account_invoice_supplier = {
				'description_financiera': comision_id.detalle_factura,
				'account_id': comision_id.partner_id.property_account_payable_id.id,
				'partner_id': comision_id.partner_id.id,
				'journal_id': journal_id.id,
				'currency_id': self.currency_id.id,
				'company_id': comision_id.company_id.id,
				'date': datetime.now(),
				'invoice_line_ids': ail_ids,
				'type': 'in_invoice',
				'payment_term_id': comision_id.account_payment_term_id.id,
			}
			new_invoice_id = self.env['account.invoice'].create(account_invoice_supplier)
			self.invoice_comisiones_ids = [new_invoice_id.id]
		return new_invoice_id

	@api.one
	def confirmar_cobrar_cuota(self, payment_date, journal_id, payment_amount, multi_cobro_id):
		rec = super(ExtendsFinancieraPrestamoCuota, self).confirmar_cobrar_cuota(payment_date, journal_id, payment_amount, multi_cobro_id)
		comisiones_ids = self.comisiones_cuota()
		for _id in comisiones_ids:
			comision_id = self.env['financiera.comision'].browse(_id)
			invoice_id = self.generar_comision(comision_id)
			self.payment_last_id.invoice_comisiones_ids = [invoice_id[0].id]

