import type {
  Schema,
  ColumnsResponse,
  SavedMappingsResponse,
  UploadResponse,
  SuggestMappingResponse,
  ValidateMappingResponse,
  SaveMappingResponse,
  SingleMappingResponse,
  PreviewResponse,
} from "../types";

export const api = {
  fetchSchema: async (): Promise<Schema> => {
    const res = await fetch("/api/schema");
    if (!res.ok) throw new Error("Failed to fetch schema");
    return res.json();
  },

  fetchColumns: async (
    fileId: string,
    hasHeader: boolean,
  ): Promise<ColumnsResponse> => {
    const res = await fetch(
      `/api/columns?file_id=${encodeURIComponent(fileId)}&has_header=${hasHeader}`,
    );
    if (!res.ok) throw new Error("Failed to load columns");
    return res.json();
  },

  fetchSavedMappings: async (): Promise<SavedMappingsResponse> => {
    const res = await fetch("/api/mappings");
    if (!res.ok) throw new Error("Failed to load mappings");
    return res.json();
  },

  uploadFile: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Upload failed.");
    }
    return res.json();
  },

  suggestMapping: async (
    fileId: string,
    hasHeader: boolean,
  ): Promise<SuggestMappingResponse> => {
    const res = await fetch(
      `/api/suggest-mapping?file_id=${encodeURIComponent(fileId)}&has_header=${hasHeader}`,
    );
    if (!res.ok) throw new Error("Failed to get suggestions");
    return res.json();
  },

  validateMapping: async (
    fileId: string,
    hasHeader: boolean,
    mapping: Record<string, string>,
  ): Promise<ValidateMappingResponse> => {
    const res = await fetch("/api/validate-mapping", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        file_id: fileId,
        has_header: hasHeader,
        mapping,
      }),
    });
    if (!res.ok) throw new Error("Failed to validate mapping");
    return res.json();
  },

  saveMapping: async (
    name: string,
    mapping: Record<string, string>,
  ): Promise<SaveMappingResponse> => {
    const formData = new FormData();
    formData.append("name", name);
    formData.append("mapping_json", JSON.stringify(mapping));

    const res = await fetch("/api/mapping", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to save mapping.");
    }
    return res.json();
  },

  saveData: async (
    fileId: string,
    hasHeader: boolean,
    mapping: Record<string, string>,
  ): Promise<SaveMappingResponse> => {
    const formData = new FormData();
    formData.append("file_id", fileId);
    formData.append("has_header", hasHeader ? "true" : "false");
    formData.append("mapping_json", JSON.stringify(mapping));

    const res = await fetch("/api/ingest-data", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to save data.");
    }
    return res.json();
  },

  fetchSingleMapping: async (id: string): Promise<SingleMappingResponse> => {
    const res = await fetch(`/api/mappings/${id}`);
    if (!res.ok) throw new Error("Failed to load mapping");
    return res.json();
  },

  fetchPreview: async (
    fileId: string,
    hasHeader: boolean,
  ): Promise<PreviewResponse> => {
    const res = await fetch(
      `/api/preview?file_id=${encodeURIComponent(fileId)}&has_header=${hasHeader}&limit=8`,
    );
    if (!res.ok) throw new Error("Failed to load preview");
    return res.json();
  },
};
