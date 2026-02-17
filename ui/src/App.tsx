import React, { useEffect, useState } from "react";
import type { Schema, CsvColumn, SavedMappingItem } from "./types";
import { api } from "./services/api";

import { UploadSection } from "./components/UploadSection";
import { MappingTable } from "./components/MappingTable";
import { ActionPanel } from "./components/ActionPanel";
import { StoragePanel } from "./components/StoragePanel";
import { PreviewTable } from "./components/PreviewTable";

const App: React.FC = () => {
  // Global State
  const [schema, setSchema] = useState<Schema | null>(null);
  const [savedMappings, setSavedMappings] = useState<SavedMappingItem[]>([]);
  const [previewRows, setPreviewRows] = useState<string[][]>([]);

  // Session State
  const [currentFileId, setCurrentFileId] = useState<string | null>(null);
  const [currentHasHeader, setCurrentHasHeader] = useState<boolean>(true);
  const [csvColumns, setCsvColumns] = useState<CsvColumn[]>([]);

  // Mapping State
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [statusMessage, setStatusMessage] = useState<string>("");

  // 1. Initial Load (Schema & Mappings)
  useEffect(() => {
    api.fetchSchema().then(setSchema).catch(console.error);
    loadSavedMappings();
  }, []);

  // 2. Load Columns & Preview & Auto-Suggest when File changes
  useEffect(() => {
    if (!currentFileId) return;

    const initFile = async () => {
      try {
        // 1. Fetch Columns
        const colData = await api.fetchColumns(currentFileId, currentHasHeader);
        setCsvColumns(colData.columns || []);

        // 2. Fetch Preview Rows
        const previewData = await api.fetchPreview(
          currentFileId,
          currentHasHeader,
        );
        setPreviewRows(previewData.rows || []);

        // 3. Run Auto-Suggest
        await handleAutoSuggest(currentFileId, currentHasHeader);
      } catch (err) {
        console.error(err);
      }
    };

    initFile();
  }, [currentFileId, currentHasHeader]);

  const loadSavedMappings = async () => {
    try {
      const data = await api.fetchSavedMappings();
      setSavedMappings(data.items || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleUploadComplete = (fileId: string, hasHeader: boolean) => {
    setMapping({});
    setCurrentFileId(fileId);
    setCurrentHasHeader(hasHeader);
  };

  const handleAutoSuggest = async (fileId: string, hasHeader: boolean) => {
    try {
      setStatusMessage("Generating suggestions...");
      const data = await api.suggestMapping(fileId, hasHeader);
      const suggestions = data.suggestions || [];
      const newMapping: Record<string, string> = {};

      let count = 0;
      for (const s of suggestions) {
        if (s.schema_field && s.confidence >= 0.5) {
          newMapping[s.schema_field] = s.csv_column;
          count++;
        }
      }
      setMapping(newMapping);
      setStatusMessage(
        count > 0
          ? `Auto-mapped ${count} columns.`
          : "No confident matches found.",
      );
    } catch (err) {
      console.error(err);
      setStatusMessage("Failed to auto-suggest.");
    }
  };

  const updateMapping = (schemaField: string, csvColumn: string) => {
    setMapping((prev) => ({
      ...prev,
      [schemaField]: csvColumn,
    }));
  };

  const triggerAutoSuggest = () => {
    if (currentFileId) {
      handleAutoSuggest(currentFileId, currentHasHeader);
    }
  };

  const hasUploadedFile = Boolean(currentFileId);

  return (
    <div className="container-fluid vh-100 d-flex flex-column p-3 bg-light overflow-hidden">
      {/* Header */}
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="fw-bold m-0">CSV Mapper</h5>
      </div>

      <div className="row flex-grow-1 g-3 overflow-hidden">
        {/* LEFT COLUMN: Controls */}
        <div className="col-md-4 col-lg-3 d-flex flex-column h-100 overflow-auto">
          {/* 1. Upload Card */}
          <div className="card shadow-sm mb-3">
            <div className="card-header py-2 bg-white fw-bold small">
              1. Upload
            </div>
            <div className="card-body p-3">
              <UploadSection
                onUploadComplete={handleUploadComplete}
                onRefreshMappings={loadSavedMappings}
              />
            </div>
          </div>
          {statusMessage && (
            <div className="badge bg-info text-dark mb-3 text-wrap">
              {statusMessage}
            </div>
          )}
          {hasUploadedFile && schema && (
            <>
              {/* 2. Actions Card */}
              <div className="card shadow-sm mb-3">
                <div className="card-header py-2 bg-white fw-bold small">
                  Actions
                </div>
                <div className="card-body p-3">
                  <ActionPanel
                    fileId={currentFileId!}
                    hasHeader={currentHasHeader}
                    mapping={mapping}
                    onApplyMapping={setMapping}
                    onTriggerAutoSuggest={triggerAutoSuggest}
                  />
                </div>
              </div>

              {/* 3. Storage Card  */}
              <div className="card shadow-sm flex-grow-1">
                <div className="card-header py-2 bg-white fw-bold small">
                  Save & Load Mappings
                </div>
                <div className="card-body p-3 overflow-auto">
                  <StoragePanel
                    fileId={currentFileId!}
                    hasHeader={currentHasHeader}
                    mapping={mapping}
                    savedMappings={savedMappings}
                    onRefreshMappings={loadSavedMappings}
                    onApplyMapping={setMapping}
                  />
                </div>
              </div>
            </>
          )}
        </div>

        {/* RIGHT COLUMN: Data (Mapping Table & Preview) */}
        <div className="col-md-8 col-lg-9 h-100 overflow-auto">
          {hasUploadedFile && schema ? (
            <div className="d-flex flex-column gap-3 h-100">
              {/* Mapping Table */}
              <div className="card shadow-sm" style={{ minHeight: "50%" }}>
                <div className="card-header py-2 bg-white fw-bold small">
                  Mapping Configuration
                </div>
                <div className="card-body p-0 overflow-auto">
                  <MappingTable
                    schema={schema}
                    csvColumns={csvColumns}
                    mapping={mapping}
                    onChangeMapping={updateMapping}
                  />
                </div>
              </div>

              {/* Preview Table */}
              <div className="card shadow-sm flex-grow-1">
                <div className="card-header py-2 bg-white fw-bold small">
                  Data Preview
                </div>
                <div className="card-body p-0 overflow-auto">
                  <PreviewTable columns={csvColumns} rows={previewRows} />
                </div>
              </div>
            </div>
          ) : (
            <div className="h-100 d-flex align-items-center justify-content-center text-muted border rounded bg-white">
              <p>Upload a file on the left to begin mapping.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;
