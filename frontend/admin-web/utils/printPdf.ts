/**
 * 打印 PDF 原文：拉取为 blob → 同源 objectURL → 隐藏 iframe → 调起系统打印。
 * （直接 iframe 跨域的 MinIO 预签名 URL 会因同源策略无法调用 print()）
 */

let printFrame: HTMLIFrameElement | null = null;

export async function printPdf(url: string): Promise<void> {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`原文获取失败 (${resp.status})`);
  const blob = await resp.blob();
  const objectUrl = URL.createObjectURL(blob);

  if (printFrame) {
    printFrame.remove();
    printFrame = null;
  }
  const frame = document.createElement("iframe");
  frame.style.position = "fixed";
  frame.style.right = "0";
  frame.style.bottom = "0";
  frame.style.width = "0";
  frame.style.height = "0";
  frame.style.border = "none";
  frame.src = objectUrl;

  await new Promise<void>((resolve, reject) => {
    frame.onload = () => resolve();
    frame.onerror = () => reject(new Error("原文加载失败"));
    document.body.appendChild(frame);
  });

  printFrame = frame;
  frame.contentWindow?.focus();
  frame.contentWindow?.print();
  // objectURL 延迟释放：打印对话框期间浏览器仍需读取内容
  setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
}
