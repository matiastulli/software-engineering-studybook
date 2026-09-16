
# Create an object called Player with name, inventory, etc
class Player:
    def __init__(self, name):
        self.name = name
        self.inventory = []

    def __repr__(self):
        return f"Player({self.name})"


player1 = Player("Alice")
player2 = Player("Bob") 
player3 = Player("Charlie")

score_and_players = [
    (20, player1),
    (10, player2),
    (15, player3)]

print(score_and_players)
score_and_players.sort(reverse=True)
print(score_and_players)

# This is not a good idea, because the Player class does not have a natural ordering.