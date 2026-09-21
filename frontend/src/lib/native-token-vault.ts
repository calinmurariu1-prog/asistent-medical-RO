import { TokenVault } from "./token-vault";

export async function createNativeTokenVault(): Promise<TokenVault> {
  const { Capacitor } = await import("@capacitor/core");
  if (!Capacitor.isNativePlatform() || !Capacitor.isPluginAvailable("SecureStorage")) {
    throw new Error("Stocarea securizată nativă nu este disponibilă. Folosește aplicația instalată.");
  }
  // Never invoke the plugin's unencrypted web implementation.
  const { SecureStorage, KeychainAccess } = await import("@aparajita/capacitor-secure-storage");
  const key = "ro.asistentmedical.session.v1";
  const vault = new TokenVault({
    read: () => SecureStorage.get(key, false, false),
    write: tokens => SecureStorage.set(key, {...tokens}, false, false, KeychainAccess.whenUnlockedThisDeviceOnly),
    remove: async () => { await SecureStorage.remove(key, false); },
  });
  await vault.initialize();
  return vault;
}
