describe("DeID capability gating", () => {
  it("toggles Ask controls based on Ollama enablement in mock mode", async () => {
    await browser.url("/");

    const inputPane = await $("section[aria-label='Input pane']");
    const initialAskButtons = await inputPane.$$(".magic-ai");
    await expect(initialAskButtons.length).toBe(0);

    const advancedButton = await $("button=⚙️ Advanced Settings");
    await advancedButton.waitForEnabled({ timeout: 15000 });
    await advancedButton.click();

    const modal = await $("[aria-label='Advanced Settings']");
    await modal.waitForDisplayed({ timeout: 15000 });

    const toggle = await modal.$("//span[normalize-space()='Enable Ollama Assist']/following::input[@type='checkbox'][1]");
    const wasChecked = await toggle.isSelected();
    if (!wasChecked) {
      await toggle.click();
      await browser.pause(800);
    }

    const closeButton = await modal.$("button=Close");
    await closeButton.click();
    await modal.waitForDisplayed({ timeout: 15000, reverse: true });

    await browser.waitUntil(
      async () => {
        const askButtons = await inputPane.$$(".magic-ai");
        return askButtons.length > 0;
      },
      { timeout: 15000, timeoutMsg: "Expected Ask controls after enabling Ollama assist." }
    );
  });
});
