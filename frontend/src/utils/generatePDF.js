import jsPDF from 'jspdf'

const COLORS = {
  blue: [21, 101, 192],
  green: [22, 163, 74],
  yellow: [245, 158, 11],
  red: [220, 38, 38],
  grey: [245, 245, 245],
  darkGrey: [66, 66, 66],
  lightGrey: [220, 220, 220],
  white: [255, 255, 255],
}

const GRADE_DESC = {
  'A+': 'Excellent - Fully Compliant',
  'A': 'Satisfactory - Compliant',
  'B': 'Needs Improvement',
  'C': 'Poor - Significant Issues',
  'D': 'Critical - Non-Compliant',
  'F': 'Fail - Non-Compliant',
}

const GRADE_COLORS = {
  'A+': COLORS.green,
  'A': COLORS.green,
  'B': COLORS.yellow,
  'C': [239, 108, 0],
  'D': COLORS.red,
  'F': COLORS.red,
}

const MARGIN = 15
const PAGE_W = 210
const PAGE_H = 297
const CONTENT_W = PAGE_W - 2 * MARGIN

function checkPage(doc, y, needed) {
  if (y + needed > PAGE_H - 20) {
    doc.addPage()
    return MARGIN
  }
  return y
}

function sectionTitle(doc, text, y) {
  y = checkPage(doc, y, 12)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(13)
  doc.setTextColor(...COLORS.blue)
  doc.text(text, MARGIN, y)
  y += 1.5
  doc.setDrawColor(...COLORS.blue)
  doc.setLineWidth(0.5)
  doc.line(MARGIN, y, PAGE_W - MARGIN, y)
  y += 5
  return y
}

function drawRow(doc, cols, y, rowH, options = {}) {
  const { bold = false, fontSize = 8, aligns = [] } = options
  let x = MARGIN
  cols.forEach((col, i) => {
    const w = options.colWidths ? options.colWidths[i] : CONTENT_W / cols.length
    doc.setFont('helvetica', bold ? 'bold' : 'normal')
    doc.setFontSize(fontSize)
    if (col.color) {
      doc.setTextColor(...col.color)
    } else {
      doc.setTextColor(...COLORS.darkGrey)
    }
    const align = aligns[i] || 'left'
    const text = String(col.text !== undefined ? col.text : col)
    if (align === 'right') {
      doc.text(text, x + w - 2, y + rowH - 2, { align: 'right' })
    } else {
      doc.text(text, x + 2, y + rowH - 2)
    }
    x += w
  })
}

function drawTable(doc, headers, rows, startY, colWidths, options = {}) {
  const { headerBg = COLORS.blue, fontSize = 8, rowH = 7 } = options
  let y = startY
  const totalW = colWidths.reduce((a, b) => a + b, 0)

  // Header row
  y = checkPage(doc, y, rowH + 2)
  doc.setFillColor(...headerBg)
  doc.rect(MARGIN, y, totalW, rowH, 'F')
  drawRow(doc, headers.map(h => ({ text: h })), y, rowH, {
    colWidths,
    fontSize,
    bold: true,
  })
  doc.setTextColor(...COLORS.white)
  // Redraw header text in white
  let x = MARGIN
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(fontSize)
  doc.setTextColor(...COLORS.white)
  headers.forEach((h, i) => {
    doc.text(h, x + 2, y + rowH - 2)
    x += colWidths[i]
  })
  y += rowH

  // Data rows
  rows.forEach((row, ri) => {
    y = checkPage(doc, y, rowH + 2)
    if (ri % 2 === 1) {
      doc.setFillColor(...COLORS.grey)
      doc.rect(MARGIN, y, totalW, rowH, 'F')
    }

    x = MARGIN
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(fontSize)
    row.forEach((cell, ci) => {
      const w = colWidths[ci]
      if (cell && typeof cell === 'object' && cell.color) {
        doc.setTextColor(...cell.color)
        doc.text(String(cell.text), x + 2, y + rowH - 2)
      } else {
        doc.setTextColor(...COLORS.darkGrey)
        doc.text(String(cell || ''), x + 2, y + rowH - 2)
      }
      x += w
    })
    y += rowH
  })

  return y + 2
}

export function generatePDF(report, score) {
  const doc = new jsPDF('p', 'mm', 'a4')
  let y = MARGIN

  // ===== TITLE =====
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(20)
  doc.setTextColor(...COLORS.blue)
  doc.text('Compliance Assessment Report', MARGIN, y + 6)
  y += 10

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(10)
  doc.setTextColor(...COLORS.darkGrey)
  doc.text('Legal Metrology (Packaged Commodities) Rules, 2011', MARGIN, y + 6)
  y += 10

  // Blue divider
  doc.setDrawColor(...COLORS.blue)
  doc.setLineWidth(1.5)
  doc.line(MARGIN, y, PAGE_W - MARGIN, y)
  y += 8

  // ===== META =====
  const metaY = y
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(9)
  doc.setTextColor(...COLORS.darkGrey)
  doc.text('Report ID:', MARGIN, metaY)
  doc.text('Generated:', MARGIN, metaY + 5)
  doc.text('Overall Status:', MARGIN, metaY + 10)

  doc.setFont('helvetica', 'normal')
  const rid = String(report.analysis_id || 'N/A')
  doc.text(rid.length > 16 ? rid.slice(0, 16) + '...' : rid, MARGIN + 35, metaY)
  doc.text(new Date().toISOString().slice(0, 19).replace('T', ' ') + ' UTC', MARGIN + 35, metaY + 5)
  doc.text(String(report.overall_status || 'PENDING'), MARGIN + 35, metaY + 10)
  y = metaY + 18

  if (!score) {
    doc.save('compliance-report.pdf')
    return doc
  }

  // ===== SCORE BOX =====
  y = checkPage(doc, y, 40)
  doc.setFillColor(...COLORS.grey)
  doc.roundedRect(MARGIN, y, CONTENT_W, 28, 2, 2, 'F')

  // Score number (left side)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(32)
  doc.setTextColor(...COLORS.blue)
  doc.text(String(Math.round(score.total_score)), MARGIN + 18, y + 17)

  doc.setFontSize(7)
  doc.setTextColor(...COLORS.darkGrey)
  doc.text('COMPLIANCE SCORE', MARGIN + 18, y + 23)

  // Grade badge (right side)
  const gc = GRADE_COLORS[score.grade] || COLORS.darkGrey
  doc.setFillColor(...gc)
  doc.roundedRect(PAGE_W - MARGIN - 28, y + 4, 23, 20, 2, 2, 'F')
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(18)
  doc.setTextColor(...COLORS.white)
  doc.text(score.grade, PAGE_W - MARGIN - 16.5, y + 17, { align: 'center' })
  doc.setFontSize(6)
  doc.text(GRADE_DESC[score.grade] || '', PAGE_W - MARGIN - 16.5, y + 21, { align: 'center' })

  y += 33

  // ===== SCORE BAR =====
  y = checkPage(doc, y, 10)
  const barW = CONTENT_W - 18
  doc.setFillColor(224, 224, 224)
  doc.roundedRect(MARGIN, y, barW, 6, 2, 2, 'F')
  const fill = (barW * score.total_score) / 100
  const barC = score.total_score >= 75 ? COLORS.green : score.total_score >= 60 ? COLORS.yellow : COLORS.red
  doc.setFillColor(...barC)
  if (fill > 1) doc.roundedRect(MARGIN, y, fill, 6, 2, 2, 'F')
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(9)
  doc.setTextColor(...COLORS.darkGrey)
  doc.text(`${Math.round(score.total_score)}%`, PAGE_W - MARGIN - 2, y + 4.5, { align: 'right' })
  y += 12

  // ===== PRIORITY TABLE =====
  const priW = [50, 30, 30, 30]
  const priRows = [
    [
      { text: 'Key Fields', color: COLORS.green },
      `${score.high_priority?.passed || 0}/${score.high_priority?.count || 0}`,
      `${(score.high_priority?.score || 0).toFixed(1)}`,
      `${(score.high_priority?.max || 0).toFixed(1)}`,
    ],
    [
      { text: 'Supporting', color: [99, 102, 241] },
      `${score.medium_priority?.passed || 0}/${score.medium_priority?.count || 0}`,
      `${(score.medium_priority?.score || 0).toFixed(1)}`,
      `${(score.medium_priority?.max || 0).toFixed(1)}`,
    ],
    [
      { text: 'Extra', color: [139, 92, 246] },
      `${score.low_priority?.passed || 0}/${score.low_priority?.count || 0}`,
      `${(score.low_priority?.score || 0).toFixed(1)}`,
      `${(score.low_priority?.max || 0).toFixed(1)}`,
    ],
  ]
  y = drawTable(doc, ['Category', 'Detected', 'Score', 'Max'], priRows, y, priW)
  y += 6

  // ===== PRODUCT INFO =====
  y = sectionTitle(doc, 'Product Information', y)
  const product = report.product || {}
  const prodFields = [
    ['Product Name', product.name || 'N/A'],
    ['Category', product.category || 'N/A'],
    ['Subcategory', product.subcategory || 'N/A'],
    ['Confidence', `${((product.classification_confidence || 0) * 100).toFixed(0)}%`],
  ]
  prodFields.forEach(([label, value]) => {
    y = checkPage(doc, y, 8)
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(8)
    doc.setTextColor(...COLORS.darkGrey)
    doc.text(label + ':', MARGIN + 2, y + 4)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(0, 0, 0)
    doc.text(String(value).slice(0, 60), MARGIN + 50, y + 4)
    y += 5.5
    doc.setDrawColor(...COLORS.lightGrey)
    doc.setLineWidth(0.3)
    doc.line(MARGIN, y, PAGE_W - MARGIN, y)
    y += 2
  })
  y += 4

  // ===== PARAMETERS TABLE =====
  y = sectionTitle(doc, 'Compliance Parameters', y)
  const paramW = [8, 42, 18, 16, 60, 26]
  const priColorMap = {
    HIGH: COLORS.green,
    MEDIUM: [99, 102, 241],
    LOW: [139, 92, 246],
  }
  const paramRows = (score.parameters || []).map((p, i) => [
    String(i + 1),
    p.name,
    { text: p.priority, color: priColorMap[p.priority] || [0, 0, 0] },
    { text: p.present ? 'PASS' : 'FAIL', color: p.present ? COLORS.green : COLORS.red },
    String(p.value || '').slice(0, 35),
    `${p.points.toFixed(1)}/${(p.weight * 100).toFixed(1)}`,
  ])
  y = drawTable(doc, ['#', 'Parameter', 'Priority', 'Status', 'Value Detected', 'Score'], paramRows, y, paramW, { fontSize: 7, rowH: 6 })
  y += 6

  // ===== RULES TABLE =====
  const rules = report.rules || []
  if (rules.length > 0) {
    y = sectionTitle(doc, 'Rule Results', y)
    const ruleW = [15, 20, 55, 80]
    const statusClr = {
      PASS: COLORS.green,
      FAIL: COLORS.red,
      REVIEW: COLORS.yellow,
      NOT_APPLICABLE: [158, 158, 158],
    }
    const ruleRows = rules.slice(0, 15).map(r => [
      `R${r.rule || r.rule_number || '?'}`,
      { text: r.status || '?', color: statusClr[r.status] || [0, 0, 0] },
      String(r.title || '').slice(0, 35),
      String(r.reason || '').slice(0, 52),
    ])
    y = drawTable(doc, ['Rule', 'Status', 'Title', 'Reason'], ruleRows, y, ruleW, { headerBg: COLORS.darkGrey, fontSize: 7, rowH: 6 })
  }

  // ===== DISCLAIMER =====
  y = checkPage(doc, y, 35)
  y += 5
  doc.setDrawColor(158, 158, 158)
  doc.setLineWidth(0.3)
  doc.line(MARGIN, y, PAGE_W - MARGIN, y)
  y += 5

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(6.5)
  doc.setTextColor(150, 150, 150)
  const discLines = doc.splitTextToSize(
    'DISCLAIMER: This report is generated from photographs of the product packaging using OCR and automated analysis. It reflects an image-based compliance assessment ONLY. Physical quantity verification and sampling/testing requirements cannot be verified from images. This is NOT a legal certificate of compliance.',
    CONTENT_W
  )
  doc.text(discLines, MARGIN, y)
  y += discLines.length * 3 + 5

  doc.setFontSize(7)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(150, 150, 150)
  doc.text('Generated by:', MARGIN, y)
  doc.setFont('helvetica', 'normal')
  doc.text('Packaged Commodities Compliance System', MARGIN + 28, y)
  y += 4
  doc.setFont('helvetica', 'bold')
  doc.text('Reference:', MARGIN, y)
  doc.setFont('helvetica', 'normal')
  doc.text('Legal Metrology (Packaged Commodities) Rules, 2011', MARGIN + 28, y)
  y += 4
  doc.setFont('helvetica', 'bold')
  doc.text('Act:', MARGIN, y)
  doc.setFont('helvetica', 'normal')
  doc.text('Legal Metrology Act, 2009', MARGIN + 28, y)

  return doc
}
