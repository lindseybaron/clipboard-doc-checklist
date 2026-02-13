const DOC_ID = '<REPLACE_WITH_DOC_ID>';
const ALLOW_PLAIN_FALLBACK = false;

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      throw new Error('Missing POST body');
    }

    var payload = JSON.parse(e.postData.contents);
    var action = payload && payload.action;
    var type = payload && payload.type;
    var section = payload && payload.section;
    var text = payload && payload.text;
    var who = payload && payload.who;

    if (String(action || '').trim().toLowerCase() === 'ensure_sections') {
      ensureSections(payload && payload.sections);
      return ContentService.createTextOutput('OK').setMimeType(ContentService.MimeType.TEXT);
    }

    if (!type || String(type).trim() === '') {
      throw new Error('Missing required field: type');
    }
    if (!section || String(section).trim() === '') {
      throw new Error('Missing required field: section');
    }
    if (!text || String(text).trim() === '') {
      throw new Error('Missing required field: text');
    }

    appendEntry(text, who, section);
    return ContentService.createTextOutput('OK').setMimeType(ContentService.MimeType.TEXT);
  } catch (err) {
    return ContentService.createTextOutput('Error: ' + err.message).setMimeType(ContentService.MimeType.TEXT);
  }
}

function ensureSections(sectionsRaw) {
  if (!Array.isArray(sectionsRaw) || sectionsRaw.length === 0) {
    throw new Error('Missing required field: sections (non-empty array)');
  }

  var seen = {};
  var sections = [];
  for (var i = 0; i < sectionsRaw.length; i++) {
    var section = String(sectionsRaw[i] || '').trim();
    if (!section || seen[section]) {
      continue;
    }
    seen[section] = true;
    sections.push(section);
  }

  if (sections.length === 0) {
    throw new Error('sections array had no valid section titles');
  }

  var doc = DocumentApp.openById(DOC_ID);
  var body = doc.getBody();
  for (var j = 0; j < sections.length; j++) {
    findOrCreateH1Section_(body, sections[j]);
  }
  doc.saveAndClose();
}

function appendEntry(textRaw, who, sectionRaw) {
  var sectionTitle = resolveSectionTitle_(sectionRaw);
  var text = String(textRaw || '').trim();
  if (!text) {
    throw new Error('text is empty after trimming');
  }

  var whoSafe = String(who || 'ME').trim() || 'ME';
  var timestamp = formatNow_();
  var line = '- ' + timestamp + ' [' + whoSafe + ']: ' + text;

  var insertionPoint = findHeadingInsertionPoint_(sectionTitle);

  // If section is missing, create heading + first checklist item atomically.
  if (!insertionPoint.found) {
    var createResult = createSectionAndFirstChecklistItemWithDocsApi_(sectionTitle, line, insertionPoint);
    if (createResult.ok) {
      return;
    }
    if (!ALLOW_PLAIN_FALLBACK) {
      throw new Error('Create section + checklist failed: ' + createResult.error);
    }
  }

  // Use Docs API checkbox bullets for true clickable checkboxes.
  var checklistResult = insertChecklistWithDocsApi_(line, insertionPoint);
  if (checklistResult.ok) {
    return;
  }

  if (!ALLOW_PLAIN_FALLBACK) {
    throw new Error('Checklist insert failed: ' + checklistResult.error);
  }

  // Optional fallback if Docs API is unavailable/misconfigured.
  var doc = DocumentApp.openById(DOC_ID);
  var body = doc.getBody();
  var loc = findOrCreateH1Section_(body, sectionTitle);
  body.insertParagraph(loc.insertionIndex, '[ ] ' + line);
  doc.saveAndClose();
}

function resolveSectionTitle_(sectionRaw) {
  var section = String(sectionRaw || '').trim();
  if (!section) {
    throw new Error('section is empty after trimming');
  }
  return section;
}

function findOrCreateH1Section_(body, sectionTitle) {
  for (var i = 0; i < body.getNumChildren(); i++) {
    var el = body.getChild(i);
    if (el.getType() !== DocumentApp.ElementType.PARAGRAPH) {
      continue;
    }

    var p = el.asParagraph();
    if (p.getHeading() === DocumentApp.ParagraphHeading.HEADING1 && p.getText() === sectionTitle) {
      return {
        headingIndex: i,
        insertionIndex: i + 1,
      };
    }
  }

  var heading = body.appendParagraph(sectionTitle);
  heading.setHeading(DocumentApp.ParagraphHeading.HEADING1);
  var headingIndex = body.getNumChildren() - 1;
  return {
    headingIndex: headingIndex,
    insertionIndex: headingIndex + 1,
  };
}

function findHeadingInsertionPoint_(sectionTitle) {
  var docJson = Docs.Documents.get(DOC_ID);
  var tabContext = getPrimaryTabContext_(docJson);
  var content = tabContext.content;
  var docEnd = getDocEndIndex_(content);

  for (var i = 0; i < content.length; i++) {
    var el = content[i];
    if (!el || !el.paragraph) {
      continue;
    }

    var style = el.paragraph.paragraphStyle || {};
    if (style.namedStyleType !== 'HEADING_1') {
      continue;
    }

    var headingText = extractParagraphText_(el).trim();
    if (headingText === sectionTitle) {
      var idx = Number(el.endIndex || 1);
      if (!isFinite(idx) || idx < 1) {
        idx = 1;
      }
      // Use paragraph end index directly; clamping here can collapse text into heading
      // when the heading is near end-of-doc.
      return {
        found: true,
        index: idx,
        tabId: tabContext.tabId,
        atDocEnd: idx >= docEnd,
      };
    }
  }

  return {
    found: false,
    index: docEnd,
    tabId: tabContext.tabId,
    atDocEnd: true,
  };
}

function insertChecklistWithDocsApi_(line, insertionPoint) {
  try {
    var start = Number(insertionPoint && insertionPoint.index);
    if (!isFinite(start) || start < 1) {
      start = 1;
    }
    var atDocEnd = !!(insertionPoint && insertionPoint.atDocEnd);
    var textToInsert = atDocEnd ? '\n' + line + '\n' : line + '\n';
    var bulletStart = atDocEnd ? start + 1 : start;
    var end = start + textToInsert.length;
    var bulletEnd = bulletStart + line.length + 1;
    var tabId = insertionPoint && insertionPoint.tabId;

    var insertLocation = { index: start };
    var bulletRange = { startIndex: bulletStart, endIndex: bulletEnd };
    if (tabId) {
      insertLocation.tabId = tabId;
      bulletRange.tabId = tabId;
    }

    Docs.Documents.batchUpdate(
      {
        requests: [
          {
            insertText: {
              location: insertLocation,
              text: textToInsert,
            },
          },
          {
            createParagraphBullets: {
              range: bulletRange,
              bulletPreset: 'BULLET_CHECKBOX',
            },
          },
        ],
      },
      DOC_ID
    );
    return { ok: true, error: '' };
  } catch (err) {
    var message = err && err.message ? err.message : String(err);
    Logger.log('Checklist insert failed: ' + message);
    return { ok: false, error: message };
  }
}

function extractParagraphText_(contentElement) {
  var paragraph = contentElement.paragraph || {};
  var elements = paragraph.elements || [];
  var out = '';
  for (var i = 0; i < elements.length; i++) {
    var textRun = elements[i] && elements[i].textRun;
    if (textRun && textRun.content) {
      out += textRun.content;
    }
  }
  return out.replace(/\n$/, '');
}

function getDocEndIndex_(content) {
  var lastEnd = 1;
  for (var i = 0; i < content.length; i++) {
    var end = Number(content[i] && content[i].endIndex);
    if (isFinite(end) && end > lastEnd) {
      lastEnd = end;
    }
  }
  return Math.max(1, lastEnd - 1);
}

function getPrimaryTabContext_(docJson) {
  var tabs = (docJson && docJson.tabs) || [];
  if (tabs.length > 0) {
    var tab = tabs[0] || {};
    var tabId = tab.tabProperties && tab.tabProperties.tabId;
    var tabContent =
      (tab.documentTab && tab.documentTab.body && tab.documentTab.body.content) || [];
    return {
      tabId: tabId || null,
      content: tabContent,
    };
  }

  return {
    tabId: null,
    content: (docJson && docJson.body && docJson.body.content) || [],
  };
}

function createSectionAndFirstChecklistItemWithDocsApi_(sectionTitle, line, insertionPoint) {
  try {
    var start = Number(insertionPoint && insertionPoint.index);
    if (!isFinite(start) || start < 1) {
      start = 1;
    }
    var tabId = insertionPoint && insertionPoint.tabId;

    // Create a new heading paragraph, then first checklist item beneath it.
    var textToInsert = '\n' + sectionTitle + '\n' + line + '\n';
    var headingStart = start + 1;
    var headingEnd = headingStart + sectionTitle.length;
    var bulletStart = headingEnd + 1;
    var bulletEnd = bulletStart + line.length + 1;

    var insertLocation = { index: start };
    var headingRange = { startIndex: headingStart, endIndex: headingEnd };
    var bulletRange = { startIndex: bulletStart, endIndex: bulletEnd };
    if (tabId) {
      insertLocation.tabId = tabId;
      headingRange.tabId = tabId;
      bulletRange.tabId = tabId;
    }

    Docs.Documents.batchUpdate(
      {
        requests: [
          {
            insertText: {
              location: insertLocation,
              text: textToInsert,
            },
          },
          {
            updateParagraphStyle: {
              range: headingRange,
              paragraphStyle: {
                namedStyleType: 'HEADING_1',
              },
              fields: 'namedStyleType',
            },
          },
          {
            createParagraphBullets: {
              range: bulletRange,
              bulletPreset: 'BULLET_CHECKBOX',
            },
          },
        ],
      },
      DOC_ID
    );
    return { ok: true, error: '' };
  } catch (err) {
    var message = err && err.message ? err.message : String(err);
    Logger.log('Create section + checklist failed: ' + message);
    return { ok: false, error: message };
  }
}

function formatNow_() {
  var fallbackTz = Session.getScriptTimeZone();
  var preferredTz = 'America/Los_Angeles';
  try {
    return Utilities.formatDate(new Date(), preferredTz, 'yyyy-MM-dd HH:mm');
  } catch (err) {
    return Utilities.formatDate(new Date(), fallbackTz, 'yyyy-MM-dd HH:mm');
  }
}
