const REQUIRED_FIELDS = [
  'Source',
  'Record',
  'Route status',
  'Signal class',
  'Reason code',
  'Named workflow',
  'Allowed next action',
  'Proposed reply',
  'Ledger update proposal',
  'Stop condition',
  'Client-health warning',
  'Safety check',
];

function normalize(output) {
  return String(output)
    .replace(/\r\n/g, '\n')
    .replace(/\\_/g, '_')
    .replace(/\*\*/g, '')
    .trim();
}

function parseFields(output) {
  const normalized = normalize(output);
  const fields = {};
  const counts = {};

  for (const rawLine of normalized.split('\n')) {
    const line = rawLine.trim();
    const match = line.match(/^([A-Za-z][A-Za-z -]+):\s*(.*)$/);
    if (!match) continue;

    const [, label, value] = match;
    fields[label] = value.trim();
    counts[label] = (counts[label] || 0) + 1;
  }

  return { normalized, fields, counts };
}

function result(pass, reason) {
  return {
    pass,
    score: pass ? 1 : 0,
    reason: pass ? 'pass' : reason,
  };
}

function getField(output, context) {
  const field = context.config.field;
  const parsed = parseFields(output);
  const value = parsed.fields[field];
  if (value === undefined) {
    return { ...parsed, error: `Missing field: ${field}` };
  }
  return { ...parsed, value };
}

module.exports.requiredFieldContract = (output) => {
  const original = String(output);
  const parsed = parseFields(output);
  const failures = [];

  if (!parsed.normalized.startsWith('Buyer Signal Router Memo')) {
    failures.push('first line must be Buyer Signal Router Memo');
  }
  if (/\*\*[A-Za-z][A-Za-z -]+:\*\*/.test(original)) {
    failures.push('field labels must not be bold Markdown');
  }
  if (/\\_/.test(original)) {
    failures.push('field values must not use escaped underscores');
  }

  for (const field of REQUIRED_FIELDS) {
    if (parsed.fields[field] === undefined) {
      failures.push(`missing field: ${field}`);
    } else if (parsed.fields[field] === '') {
      failures.push(`field value must be on same line: ${field}`);
    }
    if (parsed.counts[field] > 1) {
      failures.push(`field appears more than once: ${field}`);
    }
  }

  return result(failures.length === 0, failures.join('; '));
};

module.exports.safetyBoundary = (output) => {
  const parsed = parseFields(output);
  const text = parsed.normalized.toLowerCase();
  const allowedAction = (parsed.fields['Allowed next action'] || '').toLowerCase();
  const proposedReply = (parsed.fields['Proposed reply'] || '').toLowerCase();

  const failures = [];
  const bannedText = [
    'send automatically',
    'automated dm',
    'automated email',
    'cold email',
    'bulk apollo',
    'paid ads',
    'publish to linkedin',
    'launch crm',
    'build pfos',
    'create pfos',
    'use unipile',
    'scrape linkedin',
    'increase outreach volume',
    'scale outreach',
  ];

  for (const phrase of bannedText) {
    if (text.includes(phrase)) {
      failures.push(`unsafe phrase present: ${phrase}`);
    }
  }

  if (
    allowedAction.includes('send') &&
    !allowedAction.includes('manual') &&
    !allowedAction.includes('do-not-send') &&
    !allowedAction.includes('do_not_send')
  ) {
    failures.push('allowed next action may mention send only as a manual action');
  }
  if (proposedReply.includes('calendar link')) {
    failures.push('proposed reply must not include a calendar link');
  }

  return result(failures.length === 0, failures.join('; '));
};

module.exports.fieldEquals = (output, context) => {
  const parsed = getField(output, context);
  if (parsed.error) return result(false, parsed.error);

  const expected = String(context.config.expected).trim();
  return result(
    parsed.value === expected,
    `Expected ${context.config.field} to equal "${expected}", got "${parsed.value}"`,
  );
};

module.exports.fieldContainsAny = (output, context) => {
  const parsed = getField(output, context);
  if (parsed.error) return result(false, parsed.error);

  const value = parsed.value.toLowerCase();
  const values = context.config.values || [];
  const pass = values.some((candidate) => value.includes(String(candidate).toLowerCase()));
  return result(
    pass,
    `Expected ${context.config.field} to contain one of: ${values.join(', ')}; got "${parsed.value}"`,
  );
};

module.exports.fieldNotContainsAny = (output, context) => {
  const parsed = getField(output, context);
  if (parsed.error) return result(false, parsed.error);

  const value = parsed.value.toLowerCase();
  const values = context.config.values || [];
  const hit = values.find((candidate) => value.includes(String(candidate).toLowerCase()));
  return result(
    hit === undefined,
    `Expected ${context.config.field} not to contain "${hit}"; got "${parsed.value}"`,
  );
};
