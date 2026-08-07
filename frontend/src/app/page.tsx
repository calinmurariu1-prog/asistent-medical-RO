import Link from "next/link";
import { Activity, FileText, MessageSquare, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui";
import { LogoMark } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-provider";

const features = [
  {
    icon: FileText,
    title: "Documente & OCR",
    text: "Încarci analize (PDF, poze, DICOM); AI extrage automat valorile și un rezumat.",
  },
  {
    icon: Activity,
    title: "Analize explicate",
    text: "Fiecare parametru explicat, evidențiat și comparat în timp, cu grafice.",
  },
  {
    icon: MessageSquare,
    title: "Chat medical",
    text: "Răspunsuri bazate doar pe dosarul tău, cu surse citate.",
  },
  {
    icon: ShieldCheck,
    title: "GDPR & securitate",
    text: "Criptare, MFA și control total asupra datelor tale.",
  },
];

export default function LandingPage() {
  return (
    <main className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between p-6">
        <div className="flex items-center gap-2 font-semibold">
          <LogoMark />
          Asistent Medical AI
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Link href="/login">
            <Button variant="outline">Autentificare</Button>
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-4xl px-6 py-20 text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Dosarul tău medical,{" "}
          <span className="brand-text-gradient">înțeles pe limba ta</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted">
          Centralizează analizele și documentele, primește explicații
          orientative generate de AI și urmărește-ți sănătatea în timp.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link href="/register">
            <Button className="px-6 py-3 text-base">Începe gratuit</Button>
          </Link>
          <Link href="/login">
            <Button variant="outline" className="px-6 py-3 text-base">
              Am deja cont
            </Button>
          </Link>
        </div>
        <p className="mt-6 text-sm text-muted">
          ⚠️ Aplicația NU pune diagnostice și NU înlocuiește medicul.
        </p>
      </section>

      <section className="mx-auto grid max-w-6xl gap-5 px-6 pb-24 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((f) => (
          <div
            key={f.title}
            className="rounded-2xl border border-border bg-surface p-6 shadow-sm"
          >
            <f.icon className="mb-3 text-brand-violet" />
            <h3 className="font-semibold">{f.title}</h3>
            <p className="mt-2 text-sm text-muted">{f.text}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
