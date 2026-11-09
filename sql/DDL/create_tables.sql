IF SCHEMA_ID('silver') IS NULL EXEC('CREATE SCHEMA silver');
IF OBJECT_ID('dbo.fx_macro_indicadores', 'U') IS NULL
CREATE TABLE dbo.fx_macro_indicadores (
    data date NOT NULL,
    indicador varchar(16) NOT NULL,
    frequencia varchar(16) NOT NULL,
    valor float NOT NULL,
    fonte varchar(16) NOT NULL,
    CONSTRAINT PK_fx_macro_indicadores PRIMARY KEY (indicador, data)
);
IF OBJECT_ID('silver.usd_brl', 'U') IS NULL
CREATE TABLE silver.usd_brl (
    data date NOT NULL PRIMARY KEY,
    valor float NOT NULL CHECK (valor > 0)
);
IF OBJECT_ID('silver.eur_brl', 'U') IS NULL
CREATE TABLE silver.eur_brl (
    data date NOT NULL PRIMARY KEY,
    valor float NOT NULL CHECK (valor > 0)
);
