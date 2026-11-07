from pydantic import BaseModel, Field, model_validator
class Credentials(BaseModel):
    email:str=Field(min_length=5,max_length=180,pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password:str=Field(min_length=8,max_length=128)
class TwinInput(BaseModel):
    name:str=Field(min_length=2,max_length=100)
    institution_type:str='Commercial bank'
    geography:str='India'
    industry:str='Diversified'
    cash:float=Field(8000,ge=0,le=1e9)
    loans:float=Field(30000,ge=0,le=1e9)
    government:float=Field(7000,ge=0,le=1e9)
    bonds:float=Field(3000,ge=0,le=1e9)
    equities:float=Field(2000,ge=0,le=1e9)
    deposits:float=Field(35000,ge=0,le=1e9)
    wholesale:float=Field(10000,ge=0,le=1e9)
    @model_validator(mode='after')
    def valid_balance(self):
        if self.cash+self.loans+self.government+self.bonds+self.equities<=0: raise ValueError('Assets must be positive')
        if self.deposits+self.wholesale>self.cash+self.loans+self.government+self.bonds+self.equities: raise ValueError('Initial equity cannot be negative')
        return self
class ScenarioInput(BaseModel):
    name:str=Field(min_length=2,max_length=100)
    description:str=Field('',max_length=1000)
    severity:str=Field('moderate',pattern='^(baseline|moderate|severe|extreme)$')
    duration:int=Field(12,ge=1,le=60)
    gdp:float=Field(-2,ge=-20,le=15)
    inflation:float=Field(4,ge=0,le=30)
    interest:float=Field(100,ge=-200,le=1000)
    unemployment:float=Field(5,ge=0,le=40)
    equity_decline:float=Field(10,ge=0,le=90)
    real_estate:float=Field(10,ge=0,le=90)
    withdrawal:float=Field(5,ge=0,le=90)
    defaults:float=Field(1,ge=0,le=20)
class RunInput(BaseModel):
    twin_id:str
    scenario_id:str
class MCInput(BaseModel):
    runs:int=Field(1000,ge=100,le=5000)
    horizon:int=Field(12,ge=1,le=60)
    confidence:float=Field(.95,ge=.8,le=.999)
    volatility:float=Field(1,ge=.01,le=5)
    seed:int=Field(42,ge=0,le=2147483647)
class Decision(BaseModel):
    comment:str=Field(min_length=3,max_length=2000)
class ReportInput(BaseModel):
    run_id:str
