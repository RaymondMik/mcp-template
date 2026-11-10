CREATE TABLE IF NOT EXISTS documents (
    id      TEXT PRIMARY KEY,
    content TEXT NOT NULL
);

INSERT INTO documents (id, content) VALUES
    ('deposition.md',   'This deposition covers the testimony of Angela Smith, P.E.'),
    ('report.pdf',      'The report details the state of a 20m condenser tower.'),
    ('financials.docx', 'These financials outline the project''s budget and expenditures.'),
    ('outlook.pdf',     'This document presents the projected future performance of the system.'),
    ('plan.md',         'The plan outlines the steps for the project''s implementation.'),
    ('spec.txt',        'These specifications define the technical requirements for the equipment.')
ON CONFLICT (id) DO NOTHING;
