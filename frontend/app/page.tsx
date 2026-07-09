import type { Metadata } from "next";
import { Navbar } from "@/components/landing/navbar";
import { Hero } from "@/components/landing/hero";
import { Features } from "@/components/landing/features";
import { ConnectedLayers } from "@/components/landing/connected-layers";
import { PipelineSection } from "@/components/landing/pipeline-section";
import {
  BlastRadiusSection,
  CtaSection,
} from "@/components/landing/blast-radius";
import { FaqSection } from "@/components/landing/faq";
import { Footer } from "@/components/landing/footer";

export const metadata: Metadata = {
  title: "Knowledge graph for blast radius",
};

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">
        <Hero />
        <Features />
        <ConnectedLayers />
        <PipelineSection />
        <BlastRadiusSection />
        <FaqSection />
        <CtaSection />
      </main>
      <Footer />
    </div>
  );
}
