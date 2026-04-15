describe("DeID workbench", () => {
  it("replaces person names in output", async () => {
    await browser.url("/");

    const runButton = await $("button=Go");
    await runButton.waitForEnabled({ timeout: 15000 });

    const input = await $("textarea[placeholder='Drop or paste sensitive records...']");
    await input.setValue("Alice met Bob in London.");

    await runButton.click();

    const output = await $("section[aria-label='Output pane'] .preview");
    await browser.waitUntil(
      async () => {
        const text = await output.getText();
        return text.length > 0;
      },
      { timeout: 10000, timeoutMsg: "Expected output text after processing" }
    );

    const text = await output.getText();
    await expect(text).not.toContain("Alice");
    await expect(text).not.toContain("Bob");
  });
});
