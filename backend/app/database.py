import os, uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

def now(): return datetime.now(timezone.utc)
def uid(): return str(uuid.uuid4())
url=os.getenv('DATABASE_URL', 'sqlite:////tmp/finstress.db' if os.getenv('VERCEL') else 'sqlite:///./finstress.db')
if url.startswith('postgres://'): url=url.replace('postgres://','postgresql+psycopg://',1)
if url.startswith('postgresql://'): url=url.replace('postgresql://','postgresql+psycopg://',1)
engine=create_engine(url, connect_args={'check_same_thread':False} if url.startswith('sqlite') else {}, pool_pre_ping=True)
Session=sessionmaker(engine,expire_on_commit=False)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__='users'
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    email:Mapped[str]=mapped_column(String,unique=True,index=True)
    password:Mapped[str]=mapped_column(Text)
    role:Mapped[str]=mapped_column(String,default='analyst')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Record:
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    owner_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    data:Mapped[dict]=mapped_column(JSON)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
class Twin(Record,Base): __tablename__='digital_twins'
class Scenario(Record,Base): __tablename__='economic_scenarios'
class Run(Record,Base): __tablename__='simulation_runs'
class Approval(Record,Base): __tablename__='approval_requests'
class Audit(Record,Base): __tablename__='audit_logs'
class Report(Record,Base): __tablename__='generated_reports'
class Settings(Record,Base): __tablename__='settings'
class Execution(Record,Base): __tablename__='agent_executions'
