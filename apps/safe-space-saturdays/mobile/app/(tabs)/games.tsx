import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, router } from "expo-router";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { mobileApi, type Game, type Room } from "@/api";
import { Page, Header, ErrorState } from "@/ui";
import { themes } from "@/theme";

export default function Games() {
  const client = useQueryClient();
  const games = useQuery({
    queryKey: ["mobile-games"],
    queryFn: mobileApi.games,
    retry: 2,
  });
  const rooms = useQuery({
    queryKey: ["mobile-rooms"],
    queryFn: mobileApi.rooms,
    refetchInterval: 5000,
  });
  const [busy, setBusy] = useState<number | null>(null);
  if (games.isPending || rooms.isPending)
    return (
      <Page>
        <ActivityIndicator color={themes.sage.primary} size="large" />
      </Page>
    );
  if (games.isError || rooms.isError)
    return (
      <Page>
        <ErrorState
          message={
            (games.error ?? rooms.error)?.message ?? "Unable to load games"
          }
          onRetry={() => {
            void games.refetch();
            void rooms.refetch();
          }}
        />
      </Page>
    );
  const openRooms = rooms.data.filter((room) => room.status === "open");
  const startBot = async (game: Game) => {
    setBusy(game.id);
    try {
      const room = await mobileApi.createRoom({
        game_id: game.id,
        name: `${game.name} night`,
        max_players: Math.min(game.max_players, 2),
        fill_with_bots: true,
      });
      await mobileApi.setRoomReady(room.id);
      const session = await mobileApi.createSession(room.id, true);
      await client.invalidateQueries({ queryKey: ["mobile-rooms"] });
      return session.match_id;
    } finally {
      setBusy(null);
    }
  };
  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Header
        eyebrow="PLAY TOGETHER"
        title="Game night, your way."
        copy="Join a room, invite a friend, or start with a bot."
      />
      <Text style={styles.section}>Open rooms</Text>
      {openRooms.length === 0 ? (
        <Text style={styles.empty}>No open rooms yet. Start a game below.</Text>
      ) : (
        openRooms.map((room) => <RoomCard key={room.id} room={room} />)
      )}
      <Text style={styles.section}>Featured games</Text>
      {games.data.map((game) => (
        <View key={game.id} style={styles.card}>
          <View style={styles.icon}>
            <Text style={styles.iconText}>✦</Text>
          </View>
          <Text style={styles.name}>{game.name}</Text>
          <Text style={styles.description}>{game.description}</Text>
          <Pressable
            disabled={busy === game.id}
            onPress={async () => {
              const matchId = await startBot(game);
              if (matchId) {
                router.push(`/games/session/${matchId}`);
              }
            }}
            style={styles.button}
          >
            {busy === game.id ? (
              <ActivityIndicator color="#fffdf8" />
            ) : (
              <Text style={styles.buttonText}>Play with a bot</Text>
            )}
          </Pressable>
        </View>
      ))}
    </ScrollView>
  );
}

function RoomCard({ room }: { room: Room }) {
  return (
    <View style={styles.room}>
      <View style={styles.roomCopy}>
        <Text style={styles.roomName}>{room.name}</Text>
        <Text style={styles.description}>
          {room.game_name} · {room.participant_count}/{room.max_players} players
        </Text>
      </View>
      <Link href={`/games/rooms/${room.id}`} style={styles.join}>
        Join
      </Link>
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    backgroundColor: themes.sage.background,
    flexGrow: 1,
    padding: 24,
    paddingTop: 62,
  },
  section: {
    color: themes.sage.text,
    fontSize: 20,
    fontWeight: "800",
    marginTop: 28,
  },
  empty: { color: themes.sage.muted, fontSize: 14, marginTop: 12 },
  card: {
    backgroundColor: themes.sage.surface,
    borderColor: themes.sage.border,
    borderRadius: 22,
    borderWidth: 1,
    marginTop: 14,
    padding: 20,
  },
  icon: {
    alignItems: "center",
    backgroundColor: "#e5efe0",
    borderRadius: 14,
    height: 42,
    justifyContent: "center",
    width: 42,
  },
  iconText: { color: themes.sage.primary, fontSize: 21 },
  name: {
    color: themes.sage.text,
    fontSize: 21,
    fontWeight: "800",
    marginTop: 14,
  },
  description: {
    color: themes.sage.muted,
    fontSize: 14,
    lineHeight: 21,
    marginTop: 5,
  },
  button: {
    alignItems: "center",
    backgroundColor: themes.sage.primary,
    borderRadius: 12,
    justifyContent: "center",
    marginTop: 16,
    minHeight: 44,
  },
  buttonText: { color: "#fffdf8", fontSize: 14, fontWeight: "800" },
  room: {
    alignItems: "center",
    backgroundColor: themes.sage.surface,
    borderColor: themes.sage.border,
    borderRadius: 17,
    borderWidth: 1,
    flexDirection: "row",
    marginTop: 12,
    padding: 15,
  },
  roomCopy: { flex: 1 },
  roomName: { color: themes.sage.text, fontSize: 15, fontWeight: "800" },
  join: {
    backgroundColor: themes.sage.accent,
    borderRadius: 10,
    color: "#fffdf8",
    fontSize: 13,
    fontWeight: "800",
    overflow: "hidden",
    paddingHorizontal: 13,
    paddingVertical: 10,
  },
});
