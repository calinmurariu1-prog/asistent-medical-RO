"use client";
import {useEffect, useState, FormEvent} from "react";
import Link from "next/link";
import {api} from "@/lib/api";
import {Button, Card, Input} from "@/components/ui";

export function RecoveryForm({mode}:{mode:"forgot"|"reset"|"verify"}) {
  const [token,setToken]=useState(""); const [email,setEmail]=useState("");
  const [password,setPassword]=useState(""); const [busy,setBusy]=useState(false);
  const [error,setError]=useState(""); const [message,setMessage]=useState("");
  useEffect(()=>{
    const hash = new URLSearchParams(window.location.hash.slice(1));
    const query = new URLSearchParams(window.location.search);
    setToken(hash.get("token") || query.get("token") || "");
    window.history.replaceState(null,"",window.location.pathname);
  },[]);
  async function submit(e:FormEvent) {
    e.preventDefault();setBusy(true);setError("");
    try {
      const path=mode==="forgot"?"/auth/password-reset/request":mode==="reset"?"/auth/password-reset/confirm":"/auth/email/verify";
      const body=mode==="forgot"?{email}:mode==="reset"?{token,new_password:password}:{token};
      await api.post(path,body);
      setMessage(mode==="forgot"?"Dacă există un cont pentru această adresă, vei primi un link de recuperare.":mode==="reset"?"Parola a fost schimbată. Autentifică-te din nou.":"Adresa de email a fost confirmată.");
      setPassword("");
    } catch(e) {setError(e instanceof Error?e.message:"Serviciu indisponibil. Reîncearcă.");}
    finally {setBusy(false);}
  }
  return <main className="flex min-h-[100dvh] items-center justify-center p-6"><Card className="w-full max-w-md">
    <h1 className="mb-5 text-xl font-bold">{mode==="forgot"?"Recuperează contul":mode==="reset"?"Alege o parolă nouă":"Confirmă adresa de email"}</h1>
    {message?<p role="status">{message}</p>:<form onSubmit={submit} className="space-y-4">
      {mode==="forgot"?<label className="block">Email<Input aria-label="Email" type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} required/></label>:
        mode==="reset"?<label className="block">Parolă nouă<Input aria-label="Parolă nouă" type="password" autoComplete="new-password" minLength={8} maxLength={128} value={password} onChange={e=>setPassword(e.target.value)} required/></label>:<p>Confirmă pentru a verifica adresa asociată acestui link.</p>}
      {mode!=="forgot"&&!token&&<p role="alert">Linkul nu conține un token. Deschide din nou linkul primit.</p>}
      {error&&<p role="alert" className="text-red-600">{error}</p>}
      <Button disabled={busy||(mode!=="forgot"&&!token)} type="submit">{busy?"Se procesează…":mode==="forgot"?"Trimite linkul":mode==="reset"?"Schimbă parola":"Confirmă emailul"}</Button>
    </form>}
    <Link href="/login" className="mt-5 block text-brand-blue">Înapoi la autentificare</Link>
  </Card></main>;
}
