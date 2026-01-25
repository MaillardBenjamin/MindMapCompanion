import { useState } from "react";
import { Box, Button, List, ListItem, TextField, Typography } from "@mui/material";

type InboxPanelProps = {
  inboxItems: { id: string; raw_text: string; title?: string | null }[];
  onAdd: (text: string) => Promise<void>;
};

export default function InboxPanel({ inboxItems, onAdd }: InboxPanelProps) {
  const [text, setText] = useState("");

  const handleAdd = async () => {
    if (!text.trim()) return;
    await onAdd(text.trim());
    setText("");
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6">Inbox</Typography>
      <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Add quick idea"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <Button variant="contained" onClick={handleAdd}>
          Ajouter
        </Button>
      </Box>
      <List dense sx={{ mt: 2 }}>
        {inboxItems.map((item) => (
          <ListItem key={item.id}>{item.title || item.raw_text}</ListItem>
        ))}
      </List>
    </Box>
  );
}
