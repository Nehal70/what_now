export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export type Database = {
  __InternalSupabase: {
    PostgrestVersion: "14.5";
  };
  public: {
    Tables: {
      messages: {
        Row: {
          created_at: string;
          id: string;
          role: string;
          session_id: string;
          text: string;
        };
        Insert: {
          created_at?: string;
          id?: string;
          role: string;
          session_id: string;
          text: string;
        };
        Update: {
          created_at?: string;
          id?: string;
          role?: string;
          session_id?: string;
          text?: string;
        };
        Relationships: [
          {
            foreignKeyName: "messages_session_id_fkey";
            columns: ["session_id"];
            isOneToOne: false;
            referencedRelation: "sessions";
            referencedColumns: ["id"];
          },
        ];
      };
      profiles: {
        Row: {
          created_at: string;
          phone_e164: string;
          updated_at: string;
          user_id: string;
        };
        Insert: {
          created_at?: string;
          phone_e164: string;
          updated_at?: string;
          user_id: string;
        };
        Update: {
          created_at?: string;
          phone_e164?: string;
          updated_at?: string;
          user_id?: string;
        };
        Relationships: [];
      };
      session_images: {
        Row: {
          created_at: string;
          id: string;
          mime_type: string;
          sent_at: string | null;
          session_id: string;
          status: string;
          storage_path: string;
          user_id: string;
        };
        Insert: {
          created_at?: string;
          id?: string;
          mime_type: string;
          sent_at?: string | null;
          session_id: string;
          status?: string;
          storage_path: string;
          user_id: string;
        };
        Update: {
          created_at?: string;
          id?: string;
          mime_type?: string;
          sent_at?: string | null;
          session_id?: string;
          status?: string;
          storage_path?: string;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "session_images_session_id_fkey";
            columns: ["session_id"];
            isOneToOne: false;
            referencedRelation: "sessions";
            referencedColumns: ["id"];
          },
        ];
      };
      sessions: {
        Row: {
          call_context: Json;
          caller_phone: string;
          ended_at: string | null;
          id: string;
          livekit_room: string | null;
          phase: string | null;
          started_at: string;
          status: Database["public"]["Enums"]["session_status"];
          title: string | null;
          user_id: string;
        };
        Insert: {
          call_context?: Json;
          caller_phone: string;
          ended_at?: string | null;
          id?: string;
          livekit_room?: string | null;
          phase?: string | null;
          started_at?: string;
          status?: Database["public"]["Enums"]["session_status"];
          title?: string | null;
          user_id: string;
        };
        Update: {
          call_context?: Json;
          caller_phone?: string;
          ended_at?: string | null;
          id?: string;
          livekit_room?: string | null;
          phase?: string | null;
          started_at?: string;
          status?: Database["public"]["Enums"]["session_status"];
          title?: string | null;
          user_id?: string;
        };
        Relationships: [];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      [_ in never]: never;
    };
    Enums: {
      session_status: "active" | "completed";
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
};
