-- Ensure the correct database exists
CREATE DATABASE organizations;

-- Connect to the correct database
\c organizations

-- Create the `web_anon` role if it does not exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'web_anon') THEN
        CREATE ROLE web_anon NOLOGIN;
    END IF;
END $$;

-- Grant permissions
GRANT USAGE ON SCHEMA public TO web_anon;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO web_anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO web_anon;

CREATE TABLE IF NOT EXISTS public.organizations (
    id SERIAL PRIMARY KEY,
    ror_id TEXT UNIQUE, -- ROR identifier
    uai_id TEXT UNIQUE, -- UAI identifier
    name TEXT NOT NULL, -- Institution name
    short_name TEXT, -- Short name (from UAI `nom_court`)
    aliases TEXT[], -- Alternative names
    sector TEXT, -- Public/private from UAI
    institution_type TEXT[], -- Type (University, Research Center, etc.)
    legal_status TEXT, -- Legal status (UAI `statut_juridique_long`)
    city TEXT, -- City name
    country TEXT, -- Country
    latitude DOUBLE PRECISION, -- GPS latitude
    longitude DOUBLE PRECISION, -- GPS longitude
    address TEXT, -- Street address
    postal_code TEXT, -- Zip code
    website TEXT, -- Main website
    wikipedia TEXT, -- Wikipedia URL
    relationships JSONB, -- Parent/child relationships (from ROR)
    identifiers JSONB, -- GRID, ISNI, SIREN, Wikidata, etc.
    metadata JSONB -- Full original JSON for reference
);
