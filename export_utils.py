import csv
import io
from datetime import datetime
from database import Database, Transaction

db = Database('sqlite:///bot.db')


def get_transaction_type_text(transaction_type):
    """Возвращает текст для типа операции / Returns text for operation type"""
    type_map = {
        'give': 'Product Give',
        'return': 'Product Return',
        'sale': 'Product Sale',
        'take': 'Product Take',
        'transfer': 'Product Transfer'
    }
    return type_map.get(transaction_type, 'Unknown Operation')


def export_operations_to_csv(start_date=None, end_date=None):
    """Экспорт операций в CSV / Export operations to CSV"""
    session = db.get_session()

    try:
        query = session.query(Transaction).order_by(Transaction.created_at.desc())

        if start_date:
            query = query.filter(Transaction.created_at >= start_date)
        if end_date:
            query = query.filter(Transaction.created_at <= end_date)

        transactions = query.all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            'Date and Time',
            'Operation Type',
            'Product SKU',
            'Product Name',
            'Quantity',
            'Sender Showcase',
            'Receiver Showcase',
            'Status'
        ])

        for transaction in transactions:
            product = transaction.product
            from_vitrine = transaction.from_vitrine.username if transaction.from_vitrine else ''
            to_vitrine = transaction.to_vitrine.username if transaction.to_vitrine else ''

            writer.writerow([
                transaction.created_at.strftime('%d.%m.%Y %H:%M'),
                get_transaction_type_text(transaction.type),
                product.sku,
                product.name,
                transaction.quantity,
                from_vitrine,
                to_vitrine,
                transaction.status
            ])

        return output.getvalue()

    except Exception as e:
        print(f"❌ CSV export error: {e}")
        return None
    finally:
        session.close()