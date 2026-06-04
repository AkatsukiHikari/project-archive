// 分批渲染策略:
// 1. 读 index.html, 切成 N 个 chunk(每个 N 页),写到 /tmp
// 2. puppeteer-core 并行 / 串行渲染 N 个 PDF
// 3. pdf-lib 合并成最终 PDF
const fs = require('fs');
const path = require('path');
const os = require('os');
const puppeteer = require('puppeteer-core');
const { PDFDocument } = require('pdf-lib');

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const HTML = path.resolve(__dirname, 'index.html');
const FINAL_PDF = path.resolve(__dirname, '坤爵-智能档案管理系统-客户推介.pdf');
const CHUNK_SIZE = 5; // 每批 5 页,降低 Chrome 单次渲染压力

(async () => {
  const html = fs.readFileSync(HTML, 'utf8');

  // 切分:取 head + body 前导,再按 <section class="page"> 分块
  const headMatch = html.match(/^([\s\S]*?<body>\s*)/);
  const tailMatch = html.match(/(\s*<\/body>\s*<\/html>\s*)$/);
  if (!headMatch || !tailMatch) {
    console.error('[error] HTML 结构解析失败');
    process.exit(1);
  }
  const head = headMatch[1];
  const tail = tailMatch[1];
  const body = html.slice(head.length, html.length - tail.length);

  // 按 <section class="page" 切片(保留每个 section 完整)
  const sections = body.split(/(?=<!--\s*=+\s*\n\s*PAGE\s+\d+)/g).filter(s => s.trim());
  console.log(`[info] 找到 ${sections.length} 个页面`);

  // 分批
  const chunks = [];
  for (let i = 0; i < sections.length; i += CHUNK_SIZE) {
    chunks.push(sections.slice(i, i + CHUNK_SIZE));
  }
  console.log(`[info] 分成 ${chunks.length} 批 × ${CHUNK_SIZE} 页/批`);

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kunjue-pdf-'));
  console.log('[info] 临时目录:', tmpDir);

  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
  });

  const chunkPdfs = [];
  try {
    for (let i = 0; i < chunks.length; i++) {
      const chunkHtml = head + chunks[i].join('\n') + tail;
      const chunkHtmlPath = path.join(tmpDir, `chunk-${i + 1}.html`);
      const chunkPdfPath = path.join(tmpDir, `chunk-${i + 1}.pdf`);
      fs.writeFileSync(chunkHtmlPath, chunkHtml);

      const page = await browser.newPage();
      try {
        await page.goto('file://' + chunkHtmlPath, { waitUntil: 'networkidle0', timeout: 30000 });
        await new Promise(r => setTimeout(r, 600));
        await page.pdf({
          path: chunkPdfPath,
          format: 'A4',
          printBackground: true,
          margin: { top: 0, right: 0, bottom: 0, left: 0 },
          preferCSSPageSize: true,
          timeout: 90000,
        });
        const sz = fs.statSync(chunkPdfPath).size;
        console.log(`[ok] chunk ${i + 1}/${chunks.length} -> ${(sz / 1024).toFixed(1)} KB`);
        chunkPdfs.push(chunkPdfPath);
      } finally {
        await page.close();
      }
    }
  } catch (e) {
    console.error('[error]', e.message);
    process.exit(1);
  } finally {
    await browser.close();
  }

  // 合并 PDF
  console.log('[info] 合并', chunkPdfs.length, '份 PDF');
  const merged = await PDFDocument.create();
  for (const p of chunkPdfs) {
    const bytes = fs.readFileSync(p);
    const doc = await PDFDocument.load(bytes);
    const pages = await merged.copyPages(doc, doc.getPageIndices());
    pages.forEach(pg => merged.addPage(pg));
  }
  const finalBytes = await merged.save();
  fs.writeFileSync(FINAL_PDF, finalBytes);

  const finalSize = fs.statSync(FINAL_PDF).size;
  console.log(`[done] ${FINAL_PDF} (${(finalSize / 1024 / 1024).toFixed(2)} MB, ${merged.getPageCount()} pages)`);

  // 清理临时目录(可选)
  // fs.rmSync(tmpDir, { recursive: true, force: true });
})();
