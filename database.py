from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import ADMIN_IDS

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    role = Column(String(20), nullable=False)
    language = Column(String(5), default='ru')
    created_at = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    sku = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    type = Column(String(20), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, nullable=False)
    from_vitrine_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    to_vitrine_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    admin_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    status = Column(String(20), default='pending')
    needs_confirmation = Column(Boolean, default=False)
    confirmed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship('Product')
    from_vitrine = relationship('User', foreign_keys=[from_vitrine_id])
    to_vitrine = relationship('User', foreign_keys=[to_vitrine_id])
    admin = relationship('User', foreign_keys=[admin_id])
    confirmer = relationship('User', foreign_keys=[confirmed_by])


class Balance(Base):
    __tablename__ = 'balances'
    id = Column(Integer, primary_key=True)
    vitrine_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)

    vitrine = relationship('User')
    product = relationship('Product')


class Database:
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def init_db(self):
        # Создаем таблицы если они не существуют
        Base.metadata.create_all(bind=self.engine)
        print("✅ Таблицы проверены/созданы")

        # Добавляем тестовые данные только если таблицы пустые
        self._add_sample_data()
        self._add_admin_users()

    def _add_sample_data(self):
        """Добавляет тестовые товары только если таблица продуктов пустая"""
        session = self.get_session()
        try:
            if session.query(Product).count() == 0:
                products = [
                    Product(sku="SKU-001", name="Смартфон Samsung", description="Флагманский смартфон"),
                    Product(sku="SKU-002", name="Ноутбук HP", description="Игровой ноутбук"),
                    Product(sku="SKU-003", name="Наушники Sony", description="Беспроводные наушники"),
                ]
                session.add_all(products)
                session.commit()
                print("✅ Тестовые товары добавлены")
            else:
                print("✅ Товары уже есть в базе")
        except Exception as e:
            print(f"⚠️ Ошибка добавления товаров: {e}")
            session.rollback()
        finally:
            session.close()

    def _add_admin_users(self):
        """Добавляет администраторов из config.py в базу данных если их нет"""
        session = self.get_session()
        try:
            admins_added = 0
            for admin_id in ADMIN_IDS:
                # Проверяем, существует ли уже администратор
                existing_admin = session.query(User).filter_by(telegram_id=admin_id).first()
                if not existing_admin:
                    admin_user = User(
                        telegram_id=admin_id,
                        username=f"admin_{admin_id}",
                        role='admin',
                        language='ru'
                    )
                    session.add(admin_user)
                    admins_added += 1
                    print(f"✅ Добавлен администратор с ID: {admin_id}")
                else:
                    # Обновляем роль на admin, если пользователь уже существует но с другой ролью
                    if existing_admin.role != 'admin':
                        existing_admin.role = 'admin'
                        print(f"✅ Обновлена роль пользователя {existing_admin.username} на администратора")

            session.commit()
            if admins_added > 0:
                print(f"✅ Добавлено {admins_added} администраторов в базу данных")
            else:
                print("✅ Администраторы уже есть в базе")

        except Exception as e:
            print(f"⚠️ Ошибка добавления администраторов: {e}")
            session.rollback()
        finally:
            session.close()

    def get_session(self):
        return self.SessionLocal()