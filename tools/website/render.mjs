import { chromium } from 'playwright';
const browser = await chromium.launch({headless:true, args:['--no-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try {
  const page = await browser.newPage({viewport:{width:2048,height:1200},deviceScaleFactor:1});
  await page.goto(process.argv[2]);
  await page.waitForFunction(() => window.result !== undefined, null, {timeout: 7200000});
  const result = await page.evaluate(() => window.result);
  if (result.errors.length) throw Error(JSON.stringify(result.errors));
  console.log(`Rendered ${result.done} portraits`);
} finally { await browser.close(); }
