-- Funções SQL reutilizadas pelas tabelas da silver (rodam antes de todas as tabelas).

-- Padroniza nomes de cidade: minúsculas, sem acento, sem espaços nas pontas ou repetidos;
-- o acento agudo solto "´" (usado como apóstrofo) vira apóstrofo.
-- Ex.: '  São   Paulo ' -> 'sao paulo'; 'santa barbara d´oeste' -> 'santa barbara d''oeste'.
-- Usar a MESMA função em clientes, vendedores e geolocalização garante que a comparação
-- entre cidades de tabelas diferentes seja justa.
CREATE OR REPLACE MACRO normalize_city(city) AS
    regexp_replace(lower(strip_accents(trim(replace(city, '´', '''')))), '\s+', ' ', 'g');
