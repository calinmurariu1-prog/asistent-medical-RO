"use client";

import { useState } from "react";
import Link from "next/link";
import { ClipboardList } from "lucide-react";
import { PageHeader } from "@/components/ui";
import { RecordCollection, type CollectionSpec } from "@/components/record-collection";

const sections: Record<string, CollectionSpec> = {
  contacts: {title:"Contacte de urgență",endpoint:"/patients/me/emergency-contacts",titleKey:"name",fields:[
    {key:"name",label:"Numele persoanei",required:true,maxLength:200},
    {key:"relationship_label",label:"Relația cu persoana",maxLength:100},
    {key:"phone",label:"Telefon de contact",maxLength:40},
  ]},
  history: {title:"Istoric medical", endpoint:"/history", titleKey:"title", update:"patch", fields:[
    {key:"title",label:"Titlu",required:true,maxLength:300},
    {key:"event_type",label:"Tip înregistrare",type:"select",initial:"observation",options:[
      ["observation","Observație personală"],["diagnosis","Diagnostic menționat de medic"],
      ["chronic_condition","Afecțiune cronică"],["procedure","Procedură"],["surgery","Intervenție chirurgicală"],
      ["hospitalization","Spitalizare"],["vaccine","Vaccinare consemnată în istoric"],["treatment","Tratament consemnat"],["family_history","Istoric familial"]]},
    {key:"event_date",label:"Data evenimentului",type:"date"},
    {key:"description",label:"Detalii din document sau observații",type:"textarea",maxLength:10000},
    {key:"is_chronic",label:"Afecțiune cronică declarată",type:"checkbox"},
  ]},
  allergies: {title:"Alergii",endpoint:"/patients/me/allergies",titleKey:"substance",fields:[
    {key:"substance",label:"Substanță sau alergen",required:true,maxLength:200},
    {key:"severity",label:"Severitate declarată",type:"select",initial:"unknown",options:[
      ["unknown","Necunoscută"],["mild","Ușoară"],["moderate","Moderată"],["severe","Severă"]]},
    {key:"reaction",label:"Reacția observată",type:"textarea",maxLength:10000},
  ]},
  vaccines: {title:"Vaccinări",endpoint:"/history/vaccines",titleKey:"name",fields:[
    {key:"name",label:"Numele vaccinului",required:true,maxLength:200},
    {key:"dose",label:"Doză consemnată",maxLength:100},
    {key:"administered_on",label:"Data administrării",type:"date"},
    {key:"provider",label:"Cabinet sau furnizor",maxLength:200},
  ]},
};

export default function RecordPage() {
  const [active,setActive] = useState("history");
  const [editing,setEditing] = useState(false);
  return <div className="max-w-3xl space-y-6">
    <PageHeader title="Dosar medical" subtitle="Istoricul, alergiile, vaccinările și contactele tale, într-un singur loc." icon={ClipboardList} />
    <p className="text-sm text-muted">Introdu informații din documentele medicale sau observații personale. Înregistrările tale nu reprezintă o validare medicală.</p>
    <div className="flex flex-wrap gap-2" aria-label="Secțiuni dosar">
      {Object.entries(sections).map(([key,spec]) => <button key={key} type="button" aria-pressed={active === key}
        disabled={editing} onClick={() => setActive(key)}
        className={`min-h-12 rounded-xl border px-4 text-sm font-semibold transition disabled:opacity-60 ${active === key ? "border-brand-blue bg-brand-blue/10 text-fg" : "border-border bg-surface text-muted hover:bg-surface-2"}`}>{spec.title}</button>)}
    </div>
    {editing && <p className="text-sm text-muted">Salvează sau anulează editarea înainte de a schimba secțiunea.</p>}
    {active === "contacts" && <p className="text-sm text-muted">Păstrează aici persoanele pe care dorești să le contactezi. Aplicația nu le apelează și nu le trimite mesaje automat.</p>}
    <RecordCollection key={active} spec={sections[active]} onEditing={setEditing} />
    <Link href="/profile" className="inline-flex min-h-12 items-center text-brand-blue underline">Exportă raportul medical din Profil</Link>
  </div>;
}
