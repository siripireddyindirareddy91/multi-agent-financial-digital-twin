import type { Metadata } from 'next';
import './globals.css';
export const metadata:Metadata={title:'FINSTRESS AI | Financial Intelligence',description:'Multi-agent financial digital twin and stress testing research platform. Synthetic demonstration data.'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
