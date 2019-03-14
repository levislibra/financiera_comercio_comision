# -*- coding: utf-8 -*-
from openerp import http

# class FinancieraComercioComision(http.Controller):
#     @http.route('/financiera_comercio_comision/financiera_comercio_comision/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/financiera_comercio_comision/financiera_comercio_comision/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('financiera_comercio_comision.listing', {
#             'root': '/financiera_comercio_comision/financiera_comercio_comision',
#             'objects': http.request.env['financiera_comercio_comision.financiera_comercio_comision'].search([]),
#         })

#     @http.route('/financiera_comercio_comision/financiera_comercio_comision/objects/<model("financiera_comercio_comision.financiera_comercio_comision"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('financiera_comercio_comision.object', {
#             'object': obj
#         })