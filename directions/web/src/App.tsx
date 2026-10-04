import { lazy } from "react";
import { BrowserRouter, Route, Routes } from "react-router";
import { Layout } from "./components/Layout";

const Landing = lazy(() => import("./pages/Landing"));
const LabIndex = lazy(() => import("./pages/LabIndex"));
const Lab = lazy(() => import("./pages/Lab"));
const TrialPage = lazy(() => import("./pages/Trial"));
const Briefs = lazy(() => import("./pages/Briefs"));
const BriefPage = lazy(() => import("./pages/Brief"));
const Atlas = lazy(() => import("./pages/Atlas"));
const Results = lazy(() => import("./pages/Results"));
const About = lazy(() => import("./pages/About"));
const NotFound = lazy(() => import("./pages/NotFound"));
const Topics = lazy(() => import("./pages/Topics"));
const Start = lazy(() => import("./pages/Start"));

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, "") || undefined}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Landing />} />
          <Route path="runs" element={<LabIndex />} />
          <Route path="runs/:run" element={<Lab />} />
          <Route path="trial/:id" element={<TrialPage />} />
          <Route path="briefs" element={<Briefs />} />
          <Route path="brief/:id" element={<BriefPage />} />
          <Route path="atlas" element={<Atlas />} />
          <Route path="results" element={<Results />} />
          <Route path="about" element={<About />} />
          <Route path="topics" element={<Topics />} />
          <Route path="start" element={<Start />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
