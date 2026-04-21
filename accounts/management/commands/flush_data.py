"""
Flush all business data (products, sales, cash, purchases, expenses, etc.)
Keeps: users, roles, payment methods, cash registers, units of measure, company config.
Safe to run in production before client handoff.
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Flush all business data keeping users, roles, and system config.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes', action='store_true',
            help='Skip confirmation prompt',
        )
        parser.add_argument(
            '--flush-promotions', action='store_true',
            dest='flush_promotions',
            help='Also delete promotions (by default they are preserved)',
        )

    def handle(self, *args, **options):
        if not options['yes']:
            confirm = input(
                '\n  ATENCION: Esto borra TODOS los datos de negocio '
                '(productos, ventas, caja, compras, gastos, promociones, etc.)\n'
                '  Se mantienen: usuarios, roles, metodos de pago, cajas registradoras.\n\n'
                '  Escribi "BORRAR" para confirmar: '
            )
            if confirm != 'BORRAR':
                self.stdout.write(self.style.WARNING('Cancelado.'))
                return

        self.stdout.write(self.style.MIGRATE_HEADING('Flushing business data...'))

        with transaction.atomic():
            # 1. POS
            from pos.models import (
                POSTransactionItem, POSPayment, POSTransaction,
                POSSession, QuickAccessButton, POSKeyboardShortcut,
            )
            POSTransactionItem.objects.all().delete()
            POSPayment.objects.all().delete()
            POSTransaction.objects.all().delete()
            POSSession.objects.all().delete()
            QuickAccessButton.objects.all().delete()
            self.stdout.write('  POS (transactions, items, payments, sessions): borrado')

            # 2. Promotions — NO se borran: son configuración de negocio, no datos transaccionales.
            #    Si realmente necesitás borrarlas, usá el admin de Django o --flush-promotions.
            self.stdout.write('  Promotions: PRESERVADAS (usar --flush-promotions para borrar)')
            if options.get('flush_promotions'):
                from promotions.models import PromotionProduct, Promotion
                PromotionProduct.objects.all().delete()
                Promotion.objects.all().delete()
                self.stdout.write('  Promotions: borrado (--flush-promotions activado)')

            # 3. MercadoPago
            from mercadopago.models import PaymentIntent
            PaymentIntent.objects.all().delete()
            self.stdout.write('  MercadoPago intents: borrado')

            # 4. Signage
            from signage.models import SignItem, SignBatch
            SignItem.objects.all().delete()
            SignBatch.objects.all().delete()
            self.stdout.write('  Signage batches: borrado')

            # 5. Expenses
            from expenses.models import Expense, ExpenseCategory, RecurringExpense
            RecurringExpense.objects.all().delete()
            Expense.objects.all().delete()
            ExpenseCategory.objects.all().delete()
            self.stdout.write('  Expenses: borrado')

            # 6. Purchases
            from purchase.models import PurchaseItem, Purchase, Supplier
            PurchaseItem.objects.all().delete()
            Purchase.objects.all().delete()
            Supplier.objects.all().delete()
            self.stdout.write('  Purchases/Suppliers: borrado')

            # 7. Cash
            from cashregister.models import CashMovement, CashShift
            CashMovement.objects.all().delete()
            CashShift.objects.all().delete()
            self.stdout.write('  Cash movements/shifts: borrado')

            # 8. Stock
            from stocks.models import (
                StockMovement, ProductPackaging, Product, ProductCategory,
            )
            StockMovement.objects.all().delete()
            ProductPackaging.objects.all().delete()
            Product.objects.all().delete()
            ProductCategory.objects.all().delete()
            self.stdout.write('  Products/Stock/Categories: borrado')

            # 9. Assistant
            try:
                from assistant.models import Conversation, Message, QueryLog
                Message.objects.all().delete()
                Conversation.objects.all().delete()
                QueryLog.objects.all().delete()
                self.stdout.write('  Assistant conversations: borrado')
            except Exception:
                pass

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'Flush completado. Se mantienen: usuarios, roles, '
            'metodos de pago, cajas registradoras, unidades de medida.'
        ))
