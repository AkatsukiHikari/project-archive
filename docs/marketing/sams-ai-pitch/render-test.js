const puppeteer = require('puppeteer-core');
const HTML = process.argv[2];
const PDF = process.argv[3] || HTML.replace(/\.html$/, '.pdf');
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
  });
  try {
    const page = await browser.newPage();
    page.on('console', m => console.log('[console]', m.type(), m.text()));
    page.on('pageerror', e => console.log('[pageerror]', e.message));
    await page.goto('file://' + HTML, { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise(r => setTimeout(r, 800));
    await page.pdf({
      path: PDF, format: 'A4', printBackground: true,
      margin: {top:0,right:0,bottom:0,left:0},
      preferCSSPageSize: true,
      timeout: 90000,
    });
    console.log('[ok]', PDF);
  } catch (e) {
    console.error('[error]', e.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
